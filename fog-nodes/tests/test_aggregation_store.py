import os
import unittest
import uuid
from datetime import datetime, timezone

import redis

from aggregation_store import RedisAggregationStore


class RedisAggregationStoreIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host = os.getenv("REDIS_TEST_HOST", "localhost")
        port = int(os.getenv("REDIS_TEST_PORT", "6379"))
        cls.client = redis.Redis(
            host=host,
            port=port,
            decode_responses=True,
            socket_connect_timeout=1,
        )
        try:
            cls.client.ping()
        except redis.RedisError as exc:
            raise unittest.SkipTest(f"Redis test server is unavailable: {exc}")

    def setUp(self):
        self.prefix = f"test:sensiot:{uuid.uuid4().hex}"
        self.store = RedisAggregationStore(
            self.client,
            prefix=self.prefix,
            deduplication_ttl=60,
            outbox_visibility_timeout=2,
        )
        self.region = "eu868"

    def tearDown(self):
        keys = list(self.client.scan_iter(f"{self.prefix}:*"))
        if keys:
            self.client.delete(*keys)

    def test_aggregation_is_atomic_and_duplicate_readings_are_ignored(self):
        self.assertTrue(
            self.store.update(
                "device-1", "Sensor 1", self.region, 10, 40, False, "reading-1"
            )
        )
        self.assertFalse(
            self.store.update(
                "device-1", "Sensor 1", self.region, 99, 99, True, "reading-1"
            )
        )
        self.assertTrue(
            self.store.update(
                "device-1", "Sensor 1", self.region, 30, 60, True
            )
        )

        now = datetime.now(timezone.utc)
        self.assertEqual(self.store.flush_window(self.region, 300, now), 1)
        raw_message, message = self.store.claim_outbox_message(
            self.region, now.timestamp()
        )

        self.assertEqual(message["sample_count"], 2)
        self.assertAlmostEqual(message["avg_temperature"], 20)
        self.assertAlmostEqual(message["avg_humidity"], 50)
        self.assertTrue(message["event"])
        self.assertEqual(self.store.acknowledge_outbox_message(self.region, raw_message), 1)
        self.assertEqual(self.store.outbox_size(self.region), 0)

    def test_only_one_replica_can_flush_a_region_window(self):
        now = datetime.now(timezone.utc)
        self.store.update("device-1", "Sensor 1", self.region, 20, 50, False)

        self.assertEqual(self.store.flush_window(self.region, 300, now), 1)
        self.assertEqual(self.store.flush_window(self.region, 300, now), -1)
        self.assertEqual(self.store.outbox_size(self.region), 1)

    def test_multiple_store_instances_contribute_to_one_aggregate(self):
        replica_two = RedisAggregationStore(
            self.client,
            prefix=self.prefix,
            deduplication_ttl=60,
            outbox_visibility_timeout=2,
        )
        self.store.update("device-1", "Sensor 1", self.region, 10, 40, False)
        replica_two.update("device-1", "Sensor 1", self.region, 30, 60, False)

        now = datetime.now(timezone.utc)
        self.assertEqual(replica_two.flush_window(self.region, 300, now), 1)
        _, message = self.store.claim_outbox_message(
            self.region, now.timestamp()
        )
        self.assertEqual(message["sample_count"], 2)
        self.assertAlmostEqual(message["avg_temperature"], 20)

    def test_unacknowledged_outbox_message_becomes_visible_again(self):
        now = datetime.now(timezone.utc)
        self.store.update("device-1", "Sensor 1", self.region, 20, 50, False)
        self.store.flush_window(self.region, 300, now)

        first = self.store.claim_outbox_message(self.region, now.timestamp())
        self.assertIsNotNone(first)
        self.assertIsNone(
            self.store.claim_outbox_message(self.region, now.timestamp() + 1)
        )
        second = self.store.claim_outbox_message(self.region, now.timestamp() + 3)
        self.assertEqual(second[0], first[0])


if __name__ == "__main__":
    unittest.main()
