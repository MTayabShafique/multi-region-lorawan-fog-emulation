import os
import threading
from prometheus_client import start_http_server
import logging
import time
from mqtt_client import setup_mqtt_client
from aggregator import aggregation_worker
from publisher import publish_to_central

# Configuration via environment variables
REGION = os.getenv("REGION", "us915_0")
MQTT_BROKER = os.getenv("MQTT_BROKER", "chirpstack-docker_haproxy_1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
CENTRAL_TOPIC = os.getenv("CENTRAL_TOPIC", "central/data")
FOG_SUB_TOPIC = f"region/{REGION}/#"
AGGREGATION_INTERVAL = int(os.getenv("AGGREGATION_INTERVAL", "300"))
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "8000"))

import logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

metrics = {
    "chirpstack_fog_latency_measurements": []  # list to hold latency values for aggregation
}


def main():
    # Start Prometheus metrics server
    start_http_server(PROMETHEUS_PORT)
    logger.info(f"Started Prometheus metrics server on port {PROMETHEUS_PORT}")

    # Setup MQTT client for the fog node
    client = setup_mqtt_client(f"fog_node_{REGION}", REGION, FOG_SUB_TOPIC)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start aggregator worker thread (for aggregation and forwarding)
    threading.Thread(target=aggregation_worker, args=(client, AGGREGATION_INTERVAL, metrics), daemon=True).start()

    # Start MQTT loop (blocking)
    client.loop_forever()

if __name__ == "__main__":
    main()
