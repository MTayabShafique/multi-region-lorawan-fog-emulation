import json
import logging

logger = logging.getLogger("sensiot")
logger.setLevel(logging.INFO)


class InfluxDBConverter:
    @staticmethod
    def convert(payload):
        """
        Converts payload to InfluxDB data point format.
        :param payload: JSON string or dictionary
        :return: List of InfluxDB data points or None if conversion fails
        """
        try:
            # Parse payload if it's a JSON string
            if isinstance(payload, str):
                payload = json.loads(payload)

            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary after parsing.")

            # Extract device EUI and decoded payload
            dev_eui = payload.get("devEUI")
            decoded_payload = payload.get("decodedPayload")
            timestamp = payload.get("timestamp", None)

            if not dev_eui or not decoded_payload:
                raise ValueError("Invalid payload structure: Missing required keys.")

            # Parse decoded payload for temperature and humidity
            fields = {
                "temperature": float(decoded_payload.split(",")[1].split(":")[1].strip()),
                "humidity": float(decoded_payload.split(",")[0].split(":")[1].strip()),
            }

            # Create InfluxDB data point
            point = {
                "measurement": "sensor_data",
                "tags": {"device_eui": dev_eui},
                "fields": fields,
                "time": timestamp,  # Optional timestamp
            }

            logger.info(f"Converted payload to InfluxDB format: {point}")
            return [point]

        except json.JSONDecodeError:
            logger.error("Invalid JSON string provided.")
            return None
        except Exception as e:
            logger.error(f"Failed to convert payload: {e}")
            return None
