import logging
import json
from influxdb_client import Point

# Initialize the logger
logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)


class InfluxDBConverter:
    @staticmethod
    def convert_to_influxdb_format(payload):
        """Convert payload to InfluxDB Point format."""
        try:
            logger.debug(f"Converting payload: {payload}")

            # Decode the JSON payload correctly
            decoded_payload = json.loads(payload.get("decodedPayload", "{}"))

            # Debug decoded payload
            logger.debug(f"Decoded payload: {decoded_payload}")

            # Extract temperature and humidity from decoded payload
            fields = {
                "temperature": float(decoded_payload["temperature"]),
                "humidity": float(decoded_payload["humidity"])
            }

            # Debug extracted fields
            logger.debug(f"Extracted fields - Temperature: {fields['temperature']}, Humidity: {fields['humidity']}")

            # Create an InfluxDB Point
            point = Point("sensor_data") \
                .tag("device_eui", payload.get("devEUI")) \
                .field("temperature", fields["temperature"]) \
                .field("humidity", fields["humidity"]) \
                .time(payload.get("timestamp"))  # Optional timestamp

            return point
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to convert payload to InfluxDB format: {e}")
            return None
