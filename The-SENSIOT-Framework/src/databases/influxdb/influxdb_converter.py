import json
import logging
from influxdb_client import Point

logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)


class InfluxDBConverter:
    @staticmethod
    def convert_to_influxdb_format(payload):
        """Convert enriched payload to InfluxDB Point format."""
        try:
            logger.debug(f"Converting payload: {payload}")

            # Use sensor_data directly from payload
            sensor_data = payload.get("sensor_data", {})
            if not sensor_data:
                logger.warning("No sensor_data found in payload.")

            # Extract sensor fields; default to 0 if missing
            temperature = float(sensor_data.get("temperature", 0))
            humidity = float(sensor_data.get("humidity", 0))
            # Optionally, extract additional fields
            rssi = payload.get("rssi")
            snr = payload.get("snr")
            frequency = payload.get("frequency")
            channel = payload.get("channel")

            logger.debug(f"Extracted fields - Temperature: {temperature}, Humidity: {humidity}")

            # Create an InfluxDB Point for measurement "sensor_data"
            point = (
                Point("sensor_data")
                .tag("device_eui", payload.get("device_eui", "unknown"))
                .tag("device_name", payload.get("device_name", "unknown"))
                .tag("region", payload.get("region", "unknown"))
                .field("temperature", temperature)
                .field("humidity", humidity)
            )

            # Add additional fields if available
            if rssi is not None:
                point.field("rssi", rssi)
            if snr is not None:
                point.field("snr", snr)

            # Set the timestamp (assumes the payload's timestamp is in a valid format)
            point.time(payload.get("timestamp"))

            logger.debug(f"Created InfluxDB point: {point.to_line_protocol()}")
            return point
        except Exception as e:
            logger.error(f"Failed to convert payload to InfluxDB format: {e}")
            return None