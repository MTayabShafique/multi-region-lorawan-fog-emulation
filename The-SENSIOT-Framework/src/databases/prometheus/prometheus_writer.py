import logging
import threading
import json
from prometheus_client import start_http_server, Gauge

logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
# Avoid adding duplicate handlers
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

        # Prometheus Gauges for sensor metrics with labels for region and device_id
        self.temperature_gauge = Gauge("sensor_temperature", "Temperature of sensors", ["region", "device_id"])
        self.humidity_gauge = Gauge("sensor_humidity", "Humidity of sensors", ["region", "device_id"])
        self.rssi_gauge = Gauge("sensor_rssi", "RSSI of sensors", ["region", "device_id"])
        self.snr_gauge = Gauge("sensor_snr", "SNR of sensors", ["region", "device_id"])

        logger.info(f"{self.name} initialized successfully on port {self.port}")

    def run(self):
        logger.info(f"Started {self.name}")
        start_http_server(self.port, addr="0.0.0.0")

        while not self.event.is_set():
            self.event.wait(1)
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
        """Processes payload and updates Prometheus metrics with region and device labels."""
        try:
            if not isinstance(payload, dict):
                logger.error(f"Invalid payload format: {payload}")
                return False

            # Use device_eui from payload; default to "unknown"
            device_id = payload.get("device_eui", "unknown")
            # Use region from payload; default to "unknown"
            region = payload.get("region", "unknown")

            # Try to get sensor data either from "decodedPayload" or fallback to "sensor_data"
            if "decodedPayload" in payload:
                sensor_info = payload["decodedPayload"]
                if isinstance(sensor_info, str):
                    try:
                        sensor_info = json.loads(sensor_info)
                        logger.debug(f"Converted decodedPayload JSON string to dictionary: {sensor_info}")
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON in decodedPayload: {sensor_info}")
                        return False
            else:
                sensor_info = payload.get("sensor_data", {})

            temperature = sensor_info.get("temperature")
            humidity = sensor_info.get("humidity")
            rssi = payload.get("rssi")
            snr = payload.get("snr")

            logger.info(f"Processed Payload: Region={region}, Device={device_id}, Temp={temperature}, Humidity={humidity}, RSSI={rssi}, SNR={snr}")

            if temperature is not None:
                self.temperature_gauge.labels(region=region, device_id=device_id).set(temperature)
                logger.info(f"Updated temperature for region={region}, device_id={device_id}: {temperature}")
            else:
                logger.warning(f"Missing temperature in sensor_info: {sensor_info}")

            if humidity is not None:
                self.humidity_gauge.labels(region=region, device_id=device_id).set(humidity)
                logger.info(f"Updated humidity for region={region}, device_id={device_id}: {humidity}")
            else:
                logger.warning(f"Missing humidity in sensor_info: {sensor_info}")

            if rssi is not None:
                self.rssi_gauge.labels(region=region, device_id=device_id).set(rssi)
                logger.info(f"Updated RSSI for region={region}, device_id={device_id}: {rssi}")
            else:
                logger.warning(f"Missing rssi in payload: {payload}")

            if snr is not None:
                self.snr_gauge.labels(region=region, device_id=device_id).set(snr)
                logger.info(f"Updated SNR for region={region}, device_id={device_id}: {snr}")
            else:
                logger.warning(f"Missing snr in payload: {payload}")

            return True
        except Exception as e:
            logger.error(f"Failed to process data for Prometheus: {e}")
            return False
