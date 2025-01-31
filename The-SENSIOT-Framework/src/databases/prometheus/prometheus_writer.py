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
        self.temperature_gauge = Gauge("sensor_temperature", "Temperature of sensors", ["device_id"])
        self.humidity_gauge = Gauge("sensor_humidity", "Humidity of sensors", ["device_id"])

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
        :param payload: Data structure from MQTT queue (contains devEUI and decodedPayload)
        :return: True if successful, False otherwise
        """
        try:
            if not isinstance(payload, dict):
                logger.error(f"Invalid payload format: {payload}")
                return False

            device_id = payload.get("devEUI", "unknown_device")
            decoded_payload = payload.get("decodedPayload", "")

            if not decoded_payload:
                logger.error(f"No decoded payload found for device {device_id}")
                return False

            # Convert `decodedPayload` into a structured `objectJSON`
            sensor_data = {}
            for entry in decoded_payload.split(", "):  # Example: "Humidity: 100, Temperature: 30"
                key_value = entry.split(": ")
                if len(key_value) == 2:
                    key, value = key_value
                    sensor_data[key.lower()] = float(value)  # Convert to float

            # Simulating `objectJSON` structure
            object_json = json.dumps(sensor_data)

            # Load objectJSON safely
            parsed_data = json.loads(object_json)

            # Extract temperature and humidity
            temperature = parsed_data.get("temperature")
            humidity = parsed_data.get("humidity")

            # Update Prometheus Gauges
            if temperature is not None:
                self.temperature_gauge.labels(device_id=device_id).set(temperature)
            else:
                logger.warning(f"Temperature missing in payload: {decoded_payload}")

            if humidity is not None:
                self.humidity_gauge.labels(device_id=device_id).set(humidity)
            else:
                logger.warning(f"Humidity missing in payload: {decoded_payload}")

            return True
        except Exception as e:
            logger.error(f"Failed to process data for Prometheus: {e}")
            return False
