import logging
import os
import threading
import json
import paho.mqtt.client as mqtt
from datetime import datetime
# Import the counters from metrics.py
from metrics import received_counter, dropped_counter
from utilities.mqtt.mqtt_tls import configure_mqtt_tls

logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)

class MqttReader(threading.Thread):
    def __init__(self, name, event, queue, config):
        super().__init__()
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config

        # MQTT Broker configuration
        self.broker = self.config["broker"]
        self.port = int(self.config["port"])
        self.uplink_topic = self.config.get("topics", {}).get("processed_topic", "")
        self.keepalive = self.config["connection"]["keepalive"]
        self.username = os.getenv("MQTT_USERNAME") or self.config["connection"].get("username")
        self.password = os.getenv("MQTT_PASSWORD") or self.config["connection"].get("password")

        if not self.uplink_topic:
            logger.error("Uplink topic not specified in the configuration!")
            raise ValueError("Invalid configuration: 'uplink_topic' is required.")

        self.client = mqtt.Client()
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        configure_mqtt_tls(self.client)
        logger.info(f"{self.name} initialized successfully")

    def __connect(self):
        """Connect until the broker is ready or shutdown is requested."""
        attempt = 0
        retry_delay = 2
        max_retry_delay = 30
        while not self.event.is_set():
            attempt += 1
            try:
                self.client.connect(self.broker, self.port, self.keepalive)
                logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
                return True
            except Exception as e:
                logger.warning(
                    "Attempt %s: MQTT connection failed: %s; retrying in %ss",
                    attempt,
                    e,
                    retry_delay,
                )
                self.event.wait(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)
        return False

    def __extract_device_id(self, payload):
        """Helper to extract device ID from multiple possible fields."""
        return payload.get("device_id") or payload.get("device_eui", "unknown")

    def __on_message(self, client, userdata, msg):
        """Handle received MQTT messages with enriched payload."""
        logger.info(f"Message received from MQTT topic {msg.topic}")
        try:
            data = msg.payload.decode()
            parsed_data = json.loads(data)
            logger.debug(f"Parsed data keys: {parsed_data.keys()}")
            device_id = self.__extract_device_id(parsed_data)
            region = parsed_data.get("region", "unknown")

            # Increment Prometheus counter
            received_counter.labels(region=region, device_id=device_id).inc()

            # Queue the enriched data for further processing
            self.queue.put(parsed_data)
            logger.info(f"Enriched data queued for device_id={device_id}, region={region}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}")
            dropped_counter.labels(region="unknown", device_id="unknown").inc()
        except Exception as e:
            logger.error(f"Error while processing message: {e}")
            dropped_counter.labels(region="unknown", device_id="unknown").inc()

    def run(self):
        """Start the MQTT client and subscribe to the topic."""
        logger.info(f"Started: {self.name}")
        if not self.__connect():
            logger.info("MQTT connection cancelled during shutdown")
            return

        self.client.on_message = self.__on_message

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.info(f"✅ Successfully subscribed to {self.uplink_topic} with QoS {granted_qos}")

        self.client.on_subscribe = on_subscribe
        self.client.subscribe(self.uplink_topic, qos=1)

        self.client.loop_start()
        while not self.event.is_set():
            self.event.wait(60)

        self.client.loop_stop()
        logger.info(f"Stopped: {self.name}")
