import os
import socket
import threading
from prometheus_client import start_http_server
import logging
import time
from mqtt_client import setup_mqtt_client
from aggregator import aggregation_worker
from aggregation_store import RedisAggregationStore
from utils import get_secret

# Configuration via environment variables
REGION = os.getenv("REGION", "us915_0")
MQTT_BROKER = os.getenv("MQTT_BROKER", "fog-haproxy")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
CENTRAL_TOPIC = os.getenv("CENTRAL_TOPIC", "central/data")
FOG_SHARED_GROUP = os.getenv("FOG_SHARED_GROUP", f"fog-{REGION}")
FOG_SUB_TOPIC = os.getenv(
    "FOG_SUB_TOPIC",
    f"$share/{FOG_SHARED_GROUP}/region/{REGION}/#",
)
AGGREGATION_INTERVAL = int(os.getenv("AGGREGATION_INTERVAL", "300"))
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "8000"))
MQTT_CONNECT_RETRY_SECONDS = int(os.getenv("MQTT_CONNECT_RETRY_SECONDS", "5"))
REDIS_HOST = os.getenv("REDIS_HOST", "fog-state")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = get_secret("REDIS_PASSWORD")
REDIS_SENTINELS = [
    (host, int(port))
    for endpoint in os.getenv("REDIS_SENTINELS", "").split(",")
    if endpoint.strip()
    for host, port in [endpoint.strip().rsplit(":", 1)]
]
REDIS_MASTER_NAME = os.getenv("REDIS_MASTER_NAME", "sensiot-fog")
REDIS_SENTINEL_PASSWORD = get_secret("REDIS_SENTINEL_PASSWORD", REDIS_PASSWORD)
REDIS_CONNECT_RETRY_SECONDS = int(os.getenv("REDIS_CONNECT_RETRY_SECONDS", "5"))
DEDUPLICATION_TTL = int(os.getenv("DEDUPLICATION_TTL", "86400"))
OUTBOX_VISIBILITY_TIMEOUT = int(os.getenv("OUTBOX_VISIBILITY_TIMEOUT", "30"))
OUTBOX_POLL_INTERVAL = float(os.getenv("OUTBOX_POLL_INTERVAL", "1"))
PUBLISH_RETRY_DELAY = float(os.getenv("PUBLISH_RETRY_DELAY", "5"))

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def main():
    # Start Prometheus metrics server
    start_http_server(PROMETHEUS_PORT)
    logger.info(f"Started Prometheus metrics server on port {PROMETHEUS_PORT}")

    store_options = {
        "deduplication_ttl": DEDUPLICATION_TTL,
        "outbox_visibility_timeout": OUTBOX_VISIBILITY_TIMEOUT,
    }
    if REDIS_SENTINELS:
        aggregation_store = RedisAggregationStore.from_sentinel(
            REDIS_SENTINELS,
            REDIS_MASTER_NAME,
            REDIS_DB,
            REDIS_PASSWORD,
            REDIS_SENTINEL_PASSWORD,
            **store_options,
        )
        redis_target = f"Sentinel service {REDIS_MASTER_NAME} via {REDIS_SENTINELS}"
    else:
        aggregation_store = RedisAggregationStore.from_connection(
            REDIS_HOST,
            REDIS_PORT,
            REDIS_DB,
            REDIS_PASSWORD,
            **store_options,
        )
        redis_target = f"{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    while True:
        try:
            aggregation_store.ping()
            logger.info(f"Connected to fog state store at {redis_target}")
            break
        except Exception as e:
            logger.warning(
                f"Fog state store {redis_target} is not reachable yet: {e}. "
                f"Retrying in {REDIS_CONNECT_RETRY_SECONDS} seconds."
            )
            time.sleep(REDIS_CONNECT_RETRY_SECONDS)

    # Setup MQTT client for the fog node
    instance_id = os.getenv("FOG_INSTANCE_ID", socket.gethostname())
    client_id = f"fog_node_{REGION}_{instance_id}"
    client = setup_mqtt_client(client_id, REGION, FOG_SUB_TOPIC, aggregation_store)
    logger.info(f"[{REGION}] MQTT client identity: {client_id}")
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            break
        except OSError as e:
            logger.warning(
                f"[{REGION}] MQTT broker {MQTT_BROKER}:{MQTT_PORT} not reachable yet: {e}. "
                f"Retrying in {MQTT_CONNECT_RETRY_SECONDS} seconds."
            )
            time.sleep(MQTT_CONNECT_RETRY_SECONDS)

    # Start aggregator worker thread (for aggregation and forwarding)
    threading.Thread(
        target=aggregation_worker,
        args=(
            client,
            aggregation_store,
            REGION,
            AGGREGATION_INTERVAL,
            CENTRAL_TOPIC,
            OUTBOX_POLL_INTERVAL,
            PUBLISH_RETRY_DELAY,
        ),
        daemon=True,
    ).start()

    # Start MQTT loop (blocking)
    client.loop_forever()

if __name__ == "__main__":
    main()
