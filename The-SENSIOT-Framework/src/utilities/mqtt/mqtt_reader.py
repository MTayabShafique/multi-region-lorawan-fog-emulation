import logging
import threading
import json
import paho.mqtt.client as mqtt

# Import the counters from metrics.py
from metrics import received_counter, dropped_counter

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

        if not self.uplink_topic:
            logger.error("Uplink topic not specified in the configuration!")
            raise ValueError("Invalid configuration: 'uplink_topic' is required.")

        self.client = mqtt.Client()
        logger.info(f"{self.name} initialized successfully")

    def __connect(self):
        """Connect to the MQTT broker with retries."""
        attempts = 3
        for attempt in range(1, attempts + 1):
            try:
                self.client.connect(self.broker, self.port, self.keepalive)
                logger.info(f"Connected to MQTT broker at {self.broker}:{self.port}")
                return True
            except Exception as e:
                logger.error(f"Attempt {attempt}: Failed to connect to MQTT broker: {e}")
                if attempt < attempts:
                    self.event.wait(5)
        return False

    def __on_message(self, client, userdata, msg):
        """Handle received MQTT messages with enriched payload."""
        logger.info(f"Message received from MQTT topic {msg.topic}")
        try:
            data = msg.payload.decode()
            logger.debug(f"Raw payload: {data}")
            parsed_data = json.loads(data)

            # If the payload includes device and region information, update the received counter.
            device_id = parsed_data.get("device_eui", "unknown")
            region = parsed_data.get("region", "unknown")
            received_counter.labels(region=region, device_id=device_id).inc()

            # Queue the enriched data for further processing.
            self.queue.put(parsed_data)
            logger.info(f"Enriched data queued: {parsed_data}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}")
            # Increment the dropped counter if decoding fails
            dropped_counter.labels(region="unknown", device_id="unknown").inc()
        except Exception as e:
            logger.error(f"Error while processing message: {e}")
            dropped_counter.labels(region="unknown", device_id="unknown").inc()

    def run(self):
        """Start the MQTT client and subscribe to the topic."""
        logger.info(f"Started: {self.name}")
        if not self.__connect():
            logger.error("Exiting reader due to connection failure")
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
