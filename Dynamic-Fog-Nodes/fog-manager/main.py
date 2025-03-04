import time
import os
import logging
from src.fog_container_manager import FogContainerManager
from src.fog_mqtt_router import FogMQTTRouter
from src.mqtt_manager import MQTTManager
from src import globals as g

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Fog Manager initializing...")

    # Initialize the MQTT Router for publishing to fog nodes.
    mqtt_publisher = FogMQTTRouter()

    # Instantiate the Fog Container Manager (creates & routes messages to fog node containers)
    container_manager = FogContainerManager(
        image_name="myorg/fog-node:latest",
        mqtt_publisher=mqtt_publisher
    )

    # Save the container manager instance in globals so it can be accessed from message_processor.
    g.fog_manager = container_manager

    # Create a single MQTTManager that connects to the global broker and subscribes to uplink messages.
    mqtt_mgr = MQTTManager()
    mqtt_mgr.start()

    logger.info("✅ Fog Manager started.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Fog Manager gracefully...")
        mqtt_mgr.stop()

if __name__ == "__main__":
    main()
