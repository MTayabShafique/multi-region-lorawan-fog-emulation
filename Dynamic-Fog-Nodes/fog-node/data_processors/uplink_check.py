import base64
import json
import logging

logger = logging.getLogger("uplink_check")
logger.setLevel(logging.INFO)

def decode_base64_data(encoded_data):
    """
    Decodes a Base64-encoded string and parses it as JSON.
    Returns a dict with sensor data or an error dict.
    """
    if not encoded_data:
        logger.warning("⚠️ No data provided for decoding.")
        return {"error": "No sensor data provided"}
    try:
        logger.info("🔎 Decoding Base64-encoded sensor data.")
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str = decoded_bytes.decode("utf-8")
        sensor_data = json.loads(decoded_str)
        logger.info(f"✅ Successfully decoded sensor data: {sensor_data}")
        return sensor_data
    except json.JSONDecodeError:
        logger.warning("⚠️ Decoded Base64 is not valid JSON.")
        return {"error": "Invalid JSON format after decoding Base64"}
    except Exception as e:
        logger.error(f"❌ Error decoding Base64 data: {e}")
        return {"error": "Decoding failed"}

def extract_sensor_data(uplink_message):
    """
    Extracts sensor data from the uplink message if a 'data' field exists.
    Returns the decoded sensor data or None if not present or invalid.
    """
    if "data" in uplink_message and uplink_message["data"]:
        raw_data = uplink_message["data"]
        sensor_data = decode_base64_data(raw_data)
        if isinstance(sensor_data, dict) and "error" in sensor_data:
            logger.warning("Decoded sensor data is invalid.")
            return None
        return sensor_data
    else:
        logger.info("No sensor data found in uplink message.")
        return None
