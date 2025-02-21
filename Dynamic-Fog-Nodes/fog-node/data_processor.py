import base64
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def extract_relevant_data(uplink_message):
    """
    Extracts necessary fields from the uplink message.

    Args:
        uplink_message (dict): The original uplink message from ChirpStack.

    Returns:
        dict: Processed data containing key sensor values and metadata.
    """
    try:
        logger.info("🔍 Extracting relevant fields from uplink message.")

        # Extract basic information
        extracted_data = {
            "timestamp": uplink_message.get("time", "N/A"),
            "device_eui": uplink_message.get("deviceInfo", {}).get("devEui", "N/A"),
            "device_name": uplink_message.get("deviceInfo", {}).get("deviceName", "N/A"),
            "region": uplink_message.get("deviceInfo", {}).get("tags", {}).get("region_name", "unknown"),
            "rssi": uplink_message.get("rxInfo", [{}])[0].get("rssi", "N/A"),
            "snr": uplink_message.get("rxInfo", [{}])[0].get("snr", "N/A"),
            "frequency": uplink_message.get("txInfo", {}).get("frequency", "N/A"),
            "channel": uplink_message.get("rxInfo", [{}])[0].get("channel", "N/A"),
        }

        # Extract sensor data by decoding Base64-encoded payload
        raw_sensor_data = uplink_message.get("data", None)
        extracted_data["sensor_data"] = decode_base64_data(raw_sensor_data)

        logger.info(f"✅ Extracted relevant fields: {extracted_data}")
        return extracted_data

    except Exception as e:
        logger.error(f"❌ Error extracting data from uplink message: {e}")
        return {"error": "Failed to extract data"}


def decode_base64_data(encoded_data):
    """
    Decodes Base64-encoded sensor data and attempts to parse it as JSON.

    Args:
        encoded_data (str): Base64-encoded sensor data.

    Returns:
        dict: Decoded and parsed sensor data or an error message.
    """
    if not encoded_data:
        logger.warning("⚠️ No data field found in uplink message.")
        return {"error": "No sensor data provided"}

    try:
        logger.info("🔎 Decoding Base64-encoded sensor data.")
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_str = decoded_bytes.decode("utf-8")

        # Try to parse as JSON
        sensor_data = json.loads(decoded_str)
        logger.info(f"✅ Successfully decoded sensor data: {sensor_data}")
        return sensor_data

    except json.JSONDecodeError:
        logger.warning("⚠️ Decoded Base64 is not valid JSON.")
        return {"error": "Invalid JSON format after decoding Base64"}

    except Exception as e:
        logger.error(f"❌ Error decoding Base64 data: {e}")
        return {"error": "Decoding failed"}


def add_metadata(processed_data, fog_node_id):
    """
    Adds metadata to the processed data for tracking.

    Args:
        processed_data (dict): The extracted sensor data.
        fog_node_id (str): Identifier of the fog node processing the message.

    Returns:
        dict: Processed data with additional metadata.
    """
    try:
        logger.info("🔍 Adding metadata to processed data.")

        metadata = {
            "processed_by": fog_node_id,
            "processing_time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S")
        }

        processed_data["metadata"] = metadata
        logger.info(f"✅ Added metadata: {metadata}")
        return processed_data

    except Exception as e:
        logger.error(f"❌ Error adding metadata: {e}")
        return processed_data  # Return the data even if metadata addition fails
