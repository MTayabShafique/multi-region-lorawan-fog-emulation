import json
import logging
from influxdb_client import Point

logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)


class InfluxDBConverter:
    @staticmethod
    def convert_to_influxdb_format(payload):
        """Convert payload to InfluxDB Point format."""
        try:
            logger.debug(f"Converting payload: {payload}")

            # Ensure decodedPayload is a dictionary
            if isinstance(payload["decodedPayload"], str):
                try:
                    payload["decodedPayload"] = json.loads(payload["decodedPayload"])
                    logger.debug(f"Converted decodedPayload JSON string to dictionary: {payload['decodedPayload']}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON decodedPayload: {payload['decodedPayload']}")
                    return None

            decoded_payload = payload["decodedPayload"]

            logger.debug(f"Decoded payload: {decoded_payload}")

            # Extract temperature and humidity from decoded payload
            fields = {
                "temperature": float(decoded_payload["temperature"]),
                "humidity": float(decoded_payload["humidity"])
            }

            logger.debug(f"Extracted fields - Temperature: {fields['temperature']}, Humidity: {fields['humidity']}")

            # Create an InfluxDB Point
            point = (
                Point("sensor_data")
                .tag("device_eui", payload.get("devEUI"))
                .field("temperature", fields["temperature"])
                .field("humidity", fields["humidity"])
                .time(payload.get("timestamp"))  # Optional timestamp
            )

            return point
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to convert payload to InfluxDB format: {e}")
            return None
