import threading
import time
import logging
import os
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_message(client, userdata, msg):
    try:
        # Import message_processor dynamically to avoid circular dependencies.
        from src import message_processor
    except Exception as e:
        logger.error(f"❌ Error importing message_processor: {e}")
        return

    message_processor.on_message(client, userdata, msg)

class MQTTManager:
    def __init__(self):
        # Use environment variables for the global broker.
        self.address = os.getenv("MQTT_BROKER_GLOBAL", "haproxy")
        self.port = int(os.getenv("MQTT_PORT", 1883))
        self.client = mqtt.Client(client_id="global_uplink_client")
        self.client.on_connect = self.on_connect
        self.client.on_message = handle_message

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("📡 Connected to global MQTT broker. Subscribing to topic: application/#")
            client.subscribe("application/#")
        else:
            logger.error(f"❌ Connection failed with code {rc}")

    def start(self):
        try:
            logger.info(f"🛠️ Connecting to global MQTT broker at {self.address}:{self.port}")
            self.client.connect(self.address, self.port, keepalive=60)
            threading.Thread(target=self.client.loop_forever, daemon=True).start()
        except Exception as e:
            logger.error(f"❌ Error connecting to global MQTT broker: {e}")

    def stop(self):
        self.client.disconnect()
