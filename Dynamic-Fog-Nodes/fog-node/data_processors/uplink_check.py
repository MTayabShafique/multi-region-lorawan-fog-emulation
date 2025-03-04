import base64
import json
import logging
import ast

logger = logging.getLogger("uplink_check")
logger.setLevel(logging.INFO)


def decode_base64_data(encoded_data):
    """
    Decodes a Base64-encoded string and attempts to parse it as JSON.
    If JSON decoding fails, it attempts to use ast.literal_eval() as a fallback.

    Returns:
        dict: Parsed sensor data or an error dictionary.
    """
    if not encoded_data:
        logger.warning("⚠️ No data provided for decoding.")
        return {"error": "No sensor data provided"}

    try:
        logger.info("🔎 Decoding Base64-encoded sensor data.")
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str = decoded_bytes.decode("utf-8")
        try:
            sensor_data = json.loads(decoded_str)
            logger.info(f"✅ Successfully decoded sensor data as JSON: {sensor_data}")
            return sensor_data
        except json.JSONDecodeError:
            logger.warning("JSON decoding failed; trying ast.literal_eval() as fallback.")
            try:
                sensor_data = ast.literal_eval(decoded_str)
                if isinstance(sensor_data, dict):
                    logger.info(f"✅ Successfully parsed sensor data using ast.literal_eval: {sensor_data}")
                    return sensor_data
                else:
                    logger.error("Fallback ast.literal_eval() did not return a dictionary.")
                    return {"error": "Parsed result is not a dictionary"}
            except Exception as e:
                logger.error(f"❌ ast.literal_eval() failed: {e}")
                return {"error": "Fallback parsing failed"}
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
