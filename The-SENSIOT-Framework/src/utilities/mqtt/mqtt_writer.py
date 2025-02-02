import logging
import os
import threading
import paho.mqtt.client as mqtt
import json

# Logger setup
logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)

class MqttWriter(threading.Thread):
    def __init__(self, name, event, queue, config):
        threading.Thread.__init__(self)
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config
        self.broker = self.config["mqtt"]["broker"]
        self.port = int(self.config["mqtt"]["port"])
        self.topic_template = "application/{application_id}/device/{device_id}/command/down"
        self.client = mqtt.Client()

        logger.info("{} initialized successfully".format(self.name))

    def __connect(self):
        try:
            self.client.connect(self.broker, self.port, 60)
            logger.info("Connected to MQTT broker at {}:{}".format(self.broker, self.port))
            return True
        except Exception as e:
            logger.error("Failed to connect to MQTT broker: {}".format(e))
            return False

    def run(self):
        logger.info("Started: {}".format(self.name))
        if not self.__connect():
            logger.error("Exiting writer due to connection failure")
            return

        self.client.loop_start()

        while not self.event.is_set():
            self.event.wait(1)
            while not self.queue.empty():
                data = self.queue.get()
                if self.__publish(data):
                    logger.info("Published data to MQTT topic")
                else:
                    logger.error("Failed to publish data to MQTT topic")

        self.client.loop_stop()
        logger.info("Stopped: {}".format(self.name))

    def __publish(self, data):
        try:
            # Prepare the topic and payload
            application_id = data.get("application_id", "default_app")
            device_id = data.get("device_id", "default_device")
            topic = self.topic_template.format(application_id=application_id, device_id=device_id)
            payload = json.dumps(data)

            # Publish to MQTT topic
            self.client.publish(topic, payload=payload, qos=1)
            return True
        except Exception as e:
            logger.error(f"Error publishing to MQTT: {e}")
            return False
