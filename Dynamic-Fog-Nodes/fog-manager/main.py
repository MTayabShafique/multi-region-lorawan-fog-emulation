import time
import os
import logging
import importlib

from src.broker_discovery import BrokerDiscovery
from src.mqtt_manager import MQTTManager
from src.fog_container_manager import FogContainerManager
from src.fog_mqtt_router import FogMQTTRouter

# Set up logging (if not already configured)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Fog Manager initializing...")

    # Read environment variables for MQTT (if needed)
    mqtt_broker = os.getenv("MQTT_BROKER", "mqtt")
    mqtt_port = int(os.getenv("MQTT_PORT", 1883))

    # Initialize the MQTT Router (Handles message publishing)
    mqtt_publisher = FogMQTTRouter()

    # Instantiate Fog Container Manager (Manages dynamic fog nodes)
    container_manager = FogContainerManager(
        image_name="myorg/fog-node:latest",
        mqtt_publisher=mqtt_publisher
    )

    from src import globals as g
    g.fog_manager = container_manager

    # Inject the fog_container_manager instance into the message processor.
    # (This avoids the need for a global import inside message_processor.py.)
    #message_processor = importlib.import_module("src.message_processor")
    #message_processor.fog_manager = container_manager

    # Instantiate Broker Discovery and MQTT Manager for receiving uplink messages
    discovery = BrokerDiscovery(config_path='/app/config/brokers.json')
    mqtt_mgr = MQTTManager(discovery)

    logger.info("✅ Fog Manager started.")

    # Start MQTT Manager for handling uplink messages from brokers
    mqtt_mgr.start()

    # 🔹 Test message routing to verify MQTT connectivity
    test_message = '{"data": "Hello from Fog Manager!"}'
    region = "us915_0"  # You can change this dynamically based on test cases
    logger.info(f"📤 Sending test message to region {region}...")
    mqtt_publisher.route_message(region, test_message)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Fog Manager gracefully...")
        mqtt_mgr.stop()

if __name__ == "__main__":
    main()
