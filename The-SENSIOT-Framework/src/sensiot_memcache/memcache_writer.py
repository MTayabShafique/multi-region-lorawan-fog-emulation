import logging
import threading
import json
import memcache

logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)

class MemcacheWriter(threading.Thread):
    def __init__(self, name, event, queue, config):
        super().__init__()
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config

        self.memcache_host = self.config.get("ip", "localhost")
        self.memcache_port = int(self.config.get("port", 11211))
        self.key_expiration = int(self.config.get("key_expiration", 600))

        self.memcache_client = memcache.Client(
            [f"{self.memcache_host}:{self.memcache_port}"], debug=True
        )

        logger.info(f"{self.name} initialized successfully.")

    def __connect_memcache(self):
        try:
            logger.debug(f"Connecting to Memcached at {self.memcache_host}:{self.memcache_port}")
            self.memcache_client.set("test", "test_value", time=10)
            test_value = self.memcache_client.get("test")
            if test_value == "test_value":
                logger.info("Connected to Memcached successfully.")
                return True
            else:
                logger.error("Test value not stored or retrieved correctly from Memcached.")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to Memcached: {e}")
            return False

    def run(self):
        logger.info(f"Started: {self.name}")

        if not self.__connect_memcache():
            logger.error("Failed to connect to Memcached. Exiting.")
            return

        while not self.event.is_set():
            try:
                if not self.queue.empty():
                    payload = self.queue.get()

                    # Use 'device_eui' if available, otherwise fall back to 'device_id'
                    device_id = payload.get("device_eui", payload.get("device_id", "unknown"))

                    existing_keys = self.memcache_client.get("all_keys") or []

                    if device_id not in existing_keys:
                        existing_keys.append(device_id)
                        self.memcache_client.set("all_keys", existing_keys, time=self.key_expiration)
                        logger.debug(f"Updated key list in Memcached: {existing_keys}")

                    json_payload = json.dumps(payload)
                    self.memcache_client.set(device_id, json_payload, time=self.key_expiration)
                    logger.info(f"Stored data for device {device_id} in Memcached: {payload}")
            except Exception as e:
                logger.error(f"Error while storing data in Memcached: {e}")

        logger.info(f"Stopped: {self.name}")
