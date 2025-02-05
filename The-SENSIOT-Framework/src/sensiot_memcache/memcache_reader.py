import logging
import threading
import time
import json
import memcache

logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)


class MemcacheReader(threading.Thread):
    def __init__(self, name, event, queue, config):
        super().__init__()
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config

        # Memcache Configuration
        self.memcache_host = self.config.get("ip", "memcached")
        self.memcache_port = int(self.config.get("port", 11211))

        # Memcache Client
        self.memcache_client = memcache.Client([f"{self.memcache_host}:{self.memcache_port}"], debug=True)

        logger.info(
            f"{self.name} initialized successfully. Connecting to Memcached at {self.memcache_host}:{self.memcache_port}")

    def run(self):
        """Continuously fetch data from Memcached and push to the queue."""
        logger.info(f"Started {self.name}")

        while not self.event.is_set():
            try:
                keys = self._get_all_keys()
                if not keys:
                    logger.debug("No keys found in Memcached.")

                for key in keys:
                    payload = self.memcache_client.get(key)

                    if payload:
                        # Ensure JSON parsing
                        if isinstance(payload, str):
                            try:
                                payload = json.loads(payload)
                                logger.debug(f"Converted JSON string to dictionary: {payload}")
                            except json.JSONDecodeError:
                                logger.error(f"Failed to parse JSON from Memcached: {payload}")
                                continue

                        self.queue.put(payload)  # Push data to InfluxDB/Prometheus queue
                        logger.info(f"Fetched from Memcached: {payload}")

                time.sleep(1)  # Prevent high CPU usage
            except Exception as e:
                logger.error(f"Error reading from Memcached: {e}")

        logger.info(f"Stopped {self.name}")

    def _get_all_keys(self):
        """Retrieve all keys stored in Memcached."""
        try:
            stats = self.memcache_client.get_stats()
            keys = []

            # Attempt to use `stats cachedump` (may fail on some Memcached versions)
            for slab in stats[0][1].keys():
                if slab.startswith("items:"):
                    slab_id = slab.split(":")[1]
                    cmd = f"stats cachedump {slab_id} 100"
                    cache_dump = self.memcache_client.get_stats(cmd)
                    for entry in cache_dump:
                        keys.extend(entry[1].keys())

            if not keys:
                logger.warning("No keys retrieved using `stats cachedump`. Falling back to stored key list.")
                keys = self.memcache_client.get("all_keys")

                if keys and isinstance(keys, list):
                    logger.info(f"Retrieved keys from manually stored list: {keys}")
                else:
                    logger.debug("No backup key list found.")

            return keys if keys else []
        except Exception as e:
            logger.error(f"Error fetching Memcached keys: {e}")
            return []
