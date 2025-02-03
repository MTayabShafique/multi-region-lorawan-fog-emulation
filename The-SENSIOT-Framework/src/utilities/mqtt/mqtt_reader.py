import logging
import threading
import json
import base64
import paho.mqtt.client as mqtt

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
        self.uplink_topic = self.config.get("topics", {}).get("uplink_topic", "")
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
        """Handle received MQTT messages."""
        logger.info(f"Message received from MQTT topic {msg.topic}")
        try:
            # Decode and parse the payload
            data = msg.payload.decode()
            logger.debug(f"Raw Payload: {data}")
            parsed_data = json.loads(data)

            # Extract and decode base64 payload
            dev_eui = parsed_data.get("deviceInfo", {}).get("devEui", "Unknown")
            payload = parsed_data.get("data", "")

            if payload:
                decoded_payload = base64.b64decode(payload).decode()
                logger.info(f"Device EUI: {dev_eui}, Decoded Payload: {decoded_payload}")

                # Adding parsed and decoded data to the queue
                self.queue.put({
                    "devEUI": dev_eui,
                    "decodedPayload": decoded_payload
                    #"timestamp": parsed_data.get("rxInfo", [{}])[0].get("time"),
                })
            else:
                logger.warning("No payload found in the message.")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed: {e}")
        except Exception as e:
            logger.error(f"Error while processing message: {e}")

    def run(self):
        """Start the MQTT client and subscribe to the topic."""
        logger.info(f"Started: {self.name}")
        if not self.__connect():
            logger.error("Exiting reader due to connection failure")
            return

        self.client.on_message = self.__on_message
        self.client.subscribe(self.uplink_topic, qos=1)
        self.client.loop_start()

        while not self.event.is_set():
            self.event.wait(60)

        self.client.loop_stop()
        logger.info(f"Stopped: {self.name}")
