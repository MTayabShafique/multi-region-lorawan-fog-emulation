import paho.mqtt.client as mqtt
import os
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FogMQTTRouter:
    def __init__(self):
        # Read MQTT broker details from environment variables.
        self.broker_address = os.getenv("MQTT_BROKER_LOCAL", "haproxy_fog")
        self.broker_port = int(os.getenv("MQTT_PORT", 1883))
        self.client = mqtt.Client("fog_manager_publisher")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.connect_to_broker()

    def connect_to_broker(self):
        retries = 0
        max_retries = 10
        backoff = 3
        while retries < max_retries:
            try:
                logger.info(f"🔌 Connecting to MQTT broker at {self.broker_address}:{self.broker_port} (Attempt {retries+1})")
                self.client.connect(self.broker_address, self.broker_port, 60)
                self.client.loop_start()
                logger.info(f"✅ Connected to MQTT broker {self.broker_address}:{self.broker_port}")
                return
            except Exception as e:
                logger.error(f"❌ Connection attempt {retries+1} failed: {e}. Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2
                retries += 1
        logger.critical("❌ Max retries reached. Could not connect to MQTT broker.")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ FogMQTTRouter successfully connected to MQTT broker.")
        else:
            logger.error(f"❌ Connection failed with return code {rc}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("⚠️ Disconnected from MQTT broker. Attempting reconnection...")
            self.connect_to_broker()

    def route_message(self, region, message):
        if not region or not isinstance(region, str):
            logger.error("❌ Invalid region provided. Cannot publish message.")
            return
        topic = f"fog/{region}/process"
        logger.info(f"📤 Publishing to topic {topic}: {message}")
        result = self.client.publish(topic, message, qos=1, retain=True)  #, retain=True
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"✅ Message successfully published to {topic}")
        else:
            logger.error(f"❌ Failed to publish message to {topic}. Error code: {result.rc}")

if __name__ == "__main__":
    import threading
    router = FogMQTTRouter()
    sample_message = '{"deduplicationId": "example-id", "data": "aGVsbG8="}'
    router.route_message("eu868", sample_message)
    threading.Event().wait()
