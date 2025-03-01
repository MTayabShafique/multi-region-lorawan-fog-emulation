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

        # Prometheus Gauges for battery metrics with labels for region and device_id
        self.battery_level_gauge = Gauge("battery_level", "Battery level of sensors", ["region", "device_id"])
        self.battery_margin_gauge = Gauge("battery_margin", "Battery margin of sensors", ["region", "device_id"])
        self.external_power_gauge = Gauge("external_power_source", "External power source flag (1 = yes, 0 = no)", ["region", "device_id"])
        self.battery_unavailable_gauge = Gauge("battery_unavailable", "Battery level unavailable flag (1 = yes, 0 = no)", ["region", "device_id"])

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
        """Processes payload and updates Prometheus metrics with region and device labels."""
        try:
            if not isinstance(payload, dict):
                logger.error(f"Invalid payload format: {payload}")
                return False

            device_id = payload.get("device_eui", "unknown")
            region = payload.get("region", "unknown")

            # Extract sensor data (from sensor_data or decodedPayload if you prefer)
            sensor_info = {}
            if "decodedPayload" in payload:
                sensor_info = self._parse_decoded_payload(payload["decodedPayload"])
            else:
                sensor_info = payload.get("sensor_data", {})

            # Extract battery data if present
            battery_data = payload.get("battery_data", {})

            # Update sensor metrics if sensor data is found
            self._update_sensor_metrics(sensor_info, region, device_id)

            # Update battery metrics if battery data is found
            self._update_battery_metrics(battery_data, region, device_id)

            return True
        except Exception as e:
            logger.error(f"Failed to process data for Prometheus: {e}")
            return False

    def _parse_decoded_payload(self, decoded_payload):
        """Parse a decodedPayload if it's a JSON string; otherwise, return dict or empty."""
        if isinstance(decoded_payload, str):
            try:
                return json.loads(decoded_payload)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON in decodedPayload: {decoded_payload}")
                return {}
        elif isinstance(decoded_payload, dict):
            return decoded_payload
        return {}

    def _update_sensor_metrics(self, sensor_info, region, device_id):
        """Update Prometheus metrics for sensor data."""
        temperature = sensor_info.get("temperature")
        humidity = sensor_info.get("humidity")

        if temperature is not None:
            self.temperature_gauge.labels(region=region, device_id=device_id).set(temperature)
            logger.info(f"Updated temperature: region={region}, device_id={device_id}, value={temperature}")
        else:
            logger.debug(f"No temperature in sensor_info: {sensor_info}")

        if humidity is not None:
            self.humidity_gauge.labels(region=region, device_id=device_id).set(humidity)
            logger.info(f"Updated humidity: region={region}, device_id={device_id}, value={humidity}")
        else:
            logger.debug(f"No humidity in sensor_info: {sensor_info}")

        # If the payload includes RSSI and SNR in the top-level or sensor_info, handle them here
        rssi = sensor_info.get("rssi") or sensor_info.get("RSSI")  # or use top-level if needed
        snr = sensor_info.get("snr") or sensor_info.get("SNR")
        # If your code stores them at top-level, do:
        # rssi = payload.get("rssi")
        # snr = payload.get("snr")

        if rssi is not None:
            self.rssi_gauge.labels(region=region, device_id=device_id).set(rssi)
            logger.info(f"Updated RSSI: region={region}, device_id={device_id}, value={rssi}")

        if snr is not None:
            self.snr_gauge.labels(region=region, device_id=device_id).set(snr)
            logger.info(f"Updated SNR: region={region}, device_id={device_id}, value={snr}")

    def _update_battery_metrics(self, battery_data, region, device_id):
        """Update Prometheus metrics for battery data."""
        if not battery_data:
            logger.debug("No battery_data found in payload.")
            return

        # batteryLevel
        battery_level = battery_data.get("batteryLevel")
        if battery_level is not None:
            self.battery_level_gauge.labels(region=region, device_id=device_id).set(battery_level)
            logger.info(f"Updated batteryLevel: region={region}, device_id={device_id}, value={battery_level}")

        # margin
        margin = battery_data.get("margin")
        if margin is not None:
            self.battery_margin_gauge.labels(region=region, device_id=device_id).set(margin)
            logger.info(f"Updated battery margin: region={region}, device_id={device_id}, value={margin}")

        # externalPowerSource
        external_power = battery_data.get("externalPowerSource")
        if external_power is not None:
            value = 1 if external_power else 0
            self.external_power_gauge.labels(region=region, device_id=device_id).set(value)
            logger.info(f"Updated externalPowerSource: region={region}, device_id={device_id}, value={value}")

        # batteryLevelUnavailable
        battery_unavail = battery_data.get("batteryLevelUnavailable")
        if battery_unavail is not None:
            value = 1 if battery_unavail else 0
            self.battery_unavailable_gauge.labels(region=region, device_id=device_id).set(value)
            logger.info(f"Updated batteryLevelUnavailable: region={region}, device_id={device_id}, value={value}")
