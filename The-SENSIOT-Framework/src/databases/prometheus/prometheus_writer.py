import logging
import threading
import json
from prometheus_client import start_http_server, Gauge

logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

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
        start_http_server(self.port, addr="0.0.0.0")

        while not self.event.is_set():
            self.event.wait(1)

            # Fetch data from queue (filled by MemcacheReader)
            while not self.queue.empty():
                try:
                    payload = self.queue.get()
                    logger.info(f"Fetched sensor data from MemcacheReader queue: {payload}")
                    if self._process_data(payload):
                        logger.info("Processed payload and updated Prometheus metrics")
                    else:
                        logger.error("Failed to process data for Prometheus")
                except Exception as e:
                    logger.error(f"Unexpected error while processing queue data: {e}")

        logger.info(f"Stopped {self.name}")

    def _process_data(self, payload):
        """Processes payload and updates Prometheus metrics."""
        try:
            if not isinstance(payload, dict):
                logger.error(f"Invalid payload format: {payload}")
                return False

            device_id = payload.get("devEUI", "unknown_device")
            decoded_payload = payload.get("decodedPayload", "")

            if not decoded_payload:
                logger.error(f"No decoded payload found for device {device_id}")
                return False

            #Directly parse JSON instead of splitting strings
            if isinstance(decoded_payload, str):
                try:
                    decoded_payload = json.loads(decoded_payload)
                    logger.debug(f"Converted decodedPayload JSON string to dictionary: {decoded_payload}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON payload: {decoded_payload}")
                    return False
            elif isinstance(decoded_payload, dict):  # If it's already a dictionary, use it directly
                sensor_data = decoded_payload
            else:
                logger.error(f"Unexpected payload format: {decoded_payload}")
                return False


            temperature = decoded_payload.get("temperature")
            humidity = decoded_payload.get("humidity")


            logger.info(f"Processed Payload: Device={device_id}, Temp={temperature}, Humidity={humidity}")

            # Update Prometheus Gauges
            if temperature is not None:
                self.temperature_gauge.labels(device_id=device_id).set(temperature)
                logger.info(f"Updated Prometheus: device_id={device_id}, temperature={temperature}")
            else:
                logger.warning(f"Missing temperature in payload: {decoded_payload}")

            if humidity is not None:
                self.humidity_gauge.labels(device_id=device_id).set(humidity)
                logger.info(f"Updated Prometheus: device_id={device_id}, humidity={humidity}")
            else:
                logger.warning(f"Missing humidity in payload: {decoded_payload}")

            return True
        except Exception as e:
            logger.error(f"Failed to process data for Prometheus: {e}")
            return False
