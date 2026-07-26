import unittest
from unittest.mock import MagicMock, patch

from aggregation_store import RedisAggregationStore


class RedisSentinelTests(unittest.TestCase):
    @patch("aggregation_store.Sentinel")
    def test_sentinel_master_client_uses_authenticated_discovery(self, sentinel_factory):
        sentinel = MagicMock()
        master_client = MagicMock()
        sentinel.master_for.return_value = master_client
        sentinel_factory.return_value = sentinel

        store = RedisAggregationStore.from_sentinel(
            [("fog-sentinel1", 26379), ("fog-sentinel2", 26379)],
            "sensiot-fog",
            db=2,
            password="redis-password",
            sentinel_password="sentinel-password",
        )

        sentinel_factory.assert_called_once_with(
            [("fog-sentinel1", 26379), ("fog-sentinel2", 26379)],
            min_other_sentinels=1,
            sentinel_kwargs={
                "password": "sentinel-password",
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
            },
            password="redis-password",
            db=2,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        sentinel.master_for.assert_called_once_with("sensiot-fog")
        self.assertIs(store.client, master_client)


if __name__ == "__main__":
    unittest.main()
