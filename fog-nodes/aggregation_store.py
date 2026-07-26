import hashlib
import json
import time
import uuid
from datetime import datetime, timezone

import redis
from redis.sentinel import Sentinel


_UPDATE_AGGREGATE = """
if ARGV[7] ~= '' then
    local accepted = redis.call('SET', KEYS[3], '1', 'NX', 'EX', ARGV[8])
    if not accepted then
        return 0
    end
end

redis.call('HINCRBYFLOAT', KEYS[1], 'temperature_sum', ARGV[1])
redis.call('HINCRBYFLOAT', KEYS[1], 'humidity_sum', ARGV[2])
redis.call('HINCRBY', KEYS[1], 'count', 1)
redis.call('HSET', KEYS[1], 'device_id', ARGV[3], 'device_name', ARGV[4], 'region', ARGV[5])
if ARGV[6] == '1' then
    redis.call('HSET', KEYS[1], 'event', 1)
end
redis.call('SADD', KEYS[2], ARGV[3])
return 1
"""


_FLUSH_WINDOW = """
local marker_set = redis.call('SET', KEYS[3], '1', 'NX', 'EX', ARGV[4])
if not marker_set then
    return -1
end

local device_ids = redis.call('SMEMBERS', KEYS[1])
local queued = 0
for _, device_id in ipairs(device_ids) do
    local aggregate_key = ARGV[1] .. device_id
    local values = redis.call('HGETALL', aggregate_key)
    if #values > 0 then
        local aggregate = {}
        for i = 1, #values, 2 do
            aggregate[values[i]] = values[i + 1]
        end

        local count = tonumber(aggregate['count'])
        if count and count > 0 then
            local message = {
                aggregate_id = ARGV[2] .. ':' .. device_id,
                device_id = device_id,
                device_name = aggregate['device_name'],
                region = aggregate['region'],
                avg_temperature = tonumber(aggregate['temperature_sum']) / count,
                avg_humidity = tonumber(aggregate['humidity_sum']) / count,
                sample_count = count,
                timestamp = ARGV[3],
                event = aggregate['event'] == '1'
            }
            redis.call('ZADD', KEYS[2], ARGV[5], cjson.encode(message))
            queued = queued + 1
        end
        redis.call('DEL', aggregate_key)
    end
end
redis.call('DEL', KEYS[1])
return queued
"""


_CLAIM_OUTBOX_MESSAGE = """
local item = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
if #item == 0 or tonumber(item[2]) > tonumber(ARGV[1]) then
    return nil
end
redis.call('ZADD', KEYS[1], ARGV[2], item[1])
return item[1]
"""


class RedisAggregationStore:
    """Durable, replica-safe aggregation windows and publish outbox."""

    def __init__(
        self,
        client,
        prefix="sensiot:fog",
        deduplication_ttl=86400,
        outbox_visibility_timeout=30,
    ):
        self.client = client
        self.prefix = prefix.rstrip(":")
        self.deduplication_ttl = int(deduplication_ttl)
        self.outbox_visibility_timeout = int(outbox_visibility_timeout)
        self._update = self.client.register_script(_UPDATE_AGGREGATE)
        self._flush = self.client.register_script(_FLUSH_WINDOW)
        self._claim = self.client.register_script(_CLAIM_OUTBOX_MESSAGE)

    @classmethod
    def from_connection(
        cls,
        host,
        port=6379,
        db=0,
        password=None,
        **kwargs,
    ):
        client = redis.Redis(
            host=host,
            port=int(port),
            db=int(db),
            password=password or None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        return cls(client, **kwargs)

    @classmethod
    def from_sentinel(
        cls,
        sentinels,
        service_name,
        db=0,
        password=None,
        sentinel_password=None,
        **kwargs,
    ):
        sentinel = Sentinel(
            sentinels,
            min_other_sentinels=1,
            sentinel_kwargs={
                "password": sentinel_password or password or None,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
            },
            password=password or None,
            db=int(db),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        return cls(sentinel.master_for(service_name), **kwargs)

    def ping(self):
        return self.client.ping()

    def _region_prefix(self, region):
        return f"{self.prefix}:aggregate:{region}:"

    def _index_key(self, region):
        return f"{self.prefix}:aggregate-index:{region}"

    def _outbox_key(self, region):
        return f"{self.prefix}:outbox:{region}"

    def _deduplication_key(self, reading_id):
        digest = hashlib.sha256(str(reading_id).encode("utf-8")).hexdigest()
        return f"{self.prefix}:dedupe:{digest}"

    def update(
        self,
        device_id,
        device_name,
        region,
        temperature,
        humidity,
        event_detected,
        reading_id=None,
    ):
        aggregate_key = f"{self._region_prefix(region)}{device_id}"
        dedupe_key = self._deduplication_key(reading_id) if reading_id else f"{self.prefix}:no-dedupe"
        result = self._update(
            keys=[aggregate_key, self._index_key(region), dedupe_key],
            args=[
                temperature,
                humidity,
                device_id,
                device_name,
                region,
                "1" if event_detected else "0",
                str(reading_id) if reading_id else "",
                self.deduplication_ttl,
            ],
        )
        return bool(result)

    def flush_window(self, region, aggregation_interval, now=None):
        now = now or datetime.now(timezone.utc)
        window_number = int(now.timestamp()) // int(aggregation_interval)
        window_id = f"{region}-{window_number}-{uuid.uuid4().hex}"
        marker_key = f"{self.prefix}:flushed:{region}:{window_number}"
        marker_ttl = max(int(aggregation_interval) * 2, 60)

        return int(
            self._flush(
                keys=[self._index_key(region), self._outbox_key(region), marker_key],
                args=[
                    self._region_prefix(region),
                    window_id,
                    now.isoformat(),
                    marker_ttl,
                    now.timestamp(),
                ],
            )
        )

    def claim_outbox_message(self, region, now=None):
        now = time.time() if now is None else float(now)
        payload = self._claim(
            keys=[self._outbox_key(region)],
            args=[now, now + self.outbox_visibility_timeout],
        )
        return (payload, json.loads(payload)) if payload else None

    def acknowledge_outbox_message(self, region, raw_message):
        return self.client.zrem(self._outbox_key(region), raw_message)

    def defer_outbox_message(self, region, raw_message, retry_delay):
        return self.client.zadd(
            self._outbox_key(region),
            {raw_message: time.time() + float(retry_delay)},
        )

    def outbox_size(self, region):
        return self.client.zcard(self._outbox_key(region))
