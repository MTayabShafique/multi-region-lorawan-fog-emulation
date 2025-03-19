import logging
import threading
import json
from datetime import datetime
from prometheus_client import start_http_server, Gauge

logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

class PrometheusWriter(threading.Thread):
    def __init__(self, name, event, queue, config):
        threading.Thread.__init__(self)
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config
        self.port = int(self.config.get("port", 8000))

        # Prometheus Gauges for sensor data with labels for region and device_id
        self.temperature_gauge = Gauge("sensor_temperature", "Aggregated temperature of sensors", ["region", "device_id"])
        self.humidity_gauge = Gauge("sensor_humidity", "Aggregated humidity of sensors", ["region", "device_id"])

        logger.info(f"{self.name} initialized successfully on port {self.port}")

    def run(self):
        logger.info(f"Started {self.name}")
        start_http_server(self.port, addr="0.0.0.0")

        while not self.event.is_set():
            self.event.wait(1)
            while not self.queue.empty():
                try:
                    payload = self.queue.get()
                    logger.info(f"Fetched data from MemcacheReader queue: {payload}")
                    if self._process_data(payload):
                        logger.info("Processed payload and updated Prometheus metrics")
                    else:
                        logger.error("Failed to process data for Prometheus")
                except Exception as e:
                    logger.error(f"Unexpected error while processing queue data: {e}")

        logger.info(f"Stopped {self.name}")

    def _process_data(self, payload):
        try:
            if not isinstance(payload, dict):
                logger.error(f"Invalid payload format: {payload}")
                return False

            # Use aggregated keys from the payload
            device_id = payload.get("device_eui", payload.get("device_id", "unknown"))
            region = payload.get("region", "unknown")

            temperature = payload.get("avg_temperature")
            humidity = payload.get("avg_humidity")

            if temperature is not None:
                self.temperature_gauge.labels(region=region, device_id=device_id).set(temperature)
                logger.info(f"Updated temperature: region={region}, device_id={device_id}, value={temperature}")
            else:
                logger.debug(f"No 'avg_temperature' in payload: {payload}")

            if humidity is not None:
                self.humidity_gauge.labels(region=region, device_id=device_id).set(humidity)
                logger.info(f"Updated humidity: region={region}, device_id={device_id}, value={humidity}")
            else:
                logger.debug(f"No 'avg_humidity' in payload: {payload}")

            return True
        except Exception as e:
            logger.error(f"Failed to process data for Prometheus: {e}")
            return False
