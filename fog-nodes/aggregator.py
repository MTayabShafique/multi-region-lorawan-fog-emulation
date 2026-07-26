import logging
import time
from metrics import (
    forwarded_counter,
    avg_temperature_gauge,
    dropped_counter,
    outbox_messages_gauge,
)
from publisher import publish_to_central
from collections import defaultdict

logger = logging.getLogger(__name__)

# Local in-memory counter for published aggregated messages per region
local_published_counter = defaultdict(int)

def aggregation_worker(
    mqtt_client,
    aggregation_store,
    region,
    aggregation_interval,
    central_topic,
    outbox_poll_interval=1,
    publish_retry_delay=5,
):
    """
    Periodically move a region's aggregate window into Redis's durable outbox and
    publish due messages. Redis coordinates flushes across all replicas.
    """
    logger.info(
        f"[{region}] Aggregator worker started; interval={aggregation_interval}s, "
        f"outbox_poll={outbox_poll_interval}s"
    )
    next_flush = time.monotonic() + aggregation_interval
    while True:
        if time.monotonic() >= next_flush:
            queued = aggregation_store.flush_window(region, aggregation_interval)
            if queued >= 0:
                logger.info(f"[{region}] Queued {queued} aggregate(s) in the durable outbox")
            next_flush = time.monotonic() + aggregation_interval

        while True:
            claimed_message = aggregation_store.claim_outbox_message(region)
            if not claimed_message:
                break
            raw_message, msg = claimed_message
            try:
                publish_to_central(mqtt_client, msg, central_topic)
                forwarded_counter.labels(region=msg["region"], device_id=msg["device_id"]).inc()
                avg_temperature_gauge.labels(
                    region=msg["region"], device_id=msg["device_id"]
                ).set(msg["avg_temperature"])
                local_published_counter[msg["region"]] += 1
                aggregation_store.acknowledge_outbox_message(region, raw_message)
                logger.info(
                    f"[{region}] Forwarded aggregate {msg['aggregate_id']} "
                    f"(published total={local_published_counter[msg['region']]})"
                )
            except Exception as e:
                aggregation_store.defer_outbox_message(
                    region, raw_message, publish_retry_delay
                )
                logger.error(
                    f"[{region}] Failed to publish aggregate {msg.get('aggregate_id')}; "
                    f"retrying in {publish_retry_delay}s: {e}"
                )
                dropped_counter.labels(region=msg["region"], device_id=msg["device_id"]).inc()
                break

        outbox_messages_gauge.labels(region=region).set(
            aggregation_store.outbox_size(region)
        )
        time.sleep(min(outbox_poll_interval, max(next_flush - time.monotonic(), 0.1)))
