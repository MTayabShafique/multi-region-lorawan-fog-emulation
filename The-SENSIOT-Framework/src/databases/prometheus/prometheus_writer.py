import logging
import threading
import json
from prometheus_client import start_http_server, Gauge

logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)

class PrometheusWriter(threading.Thread):
    def __init__(self, name, event, queue, config):
        threading.Thread.__init__(self)
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config
        self.port = int(self.config.get("port", 8000))

        # Prometheus Gauges for temperature and humidity
        self.temperature_gauge = Gauge("sensor_temperature", "Temperature of sensors", ["device_id", "application_id"])
        self.humidity_gauge = Gauge("sensor_humidity", "Humidity of sensors", ["device_id", "application_id"])

        logger.info(f"{self.name} initialized successfully on port {self.port}")

    def run(self):
        logger.info(f"Started {self.name}")
        start_http_server(self.port)

        while not self.event.is_set():
            self.event.wait(1)
            while not self.queue.empty():
                data = self.queue.get()
                if self.__process_data(data):
                    logger.info("Processed data and updated Prometheus metrics")
                else:
                    logger.error("Failed to process data for Prometheus")

        logger.info(f"Stopped {self.name}")

    def __process_data(self, payload):
        """
        Processes MQTT payload and updates Prometheus metrics.
        :param payload: Raw payload from MQTT message (JSON format)
        :return: True if successful, False otherwise
        """
        try:
            # Parse JSON payload
            data = json.loads(payload)
            device_id = data["devEUI"]
            application_id = data.get("applicationID", "unknown_app")

            # Extract sensor fields (temperature and humidity)
            fields = data.get("objectJSON")
            if fields is None:
                logger.error("No objectJSON found in payload: {}".format(payload))
                return False

            sensor_data = json.loads(fields)
            temperature = sensor_data.get("temperature")
            humidity = sensor_data.get("humidity")

            # Update Prometheus Gauges
            if temperature is not None:
                self.temperature_gauge.labels(device_id=device_id, application_id=application_id).set(temperature)
            if humidity is not None:
                self.humidity_gauge.labels(device_id=device_id, application_id=application_id).set(humidity)

            return True
        except Exception as e:
            logger.error(f"Failed to process data for Prometheus: {e}")
            return False
