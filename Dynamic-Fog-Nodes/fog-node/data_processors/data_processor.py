import json
import logging
from datetime import datetime
from data_processors.uplink_check import extract_sensor_data
from data_processors.battery_processor import extract_battery_info

logger = logging.getLogger("data_processor")
logger.setLevel(logging.INFO)


def extract_relevant_data(uplink_message):
    """
    Extracts common fields from the uplink message.

    - If valid sensor data is available (decoded from the "data" field), it is added under "sensor_data"
      and sensor-specific fields (rssi, snr, frequency, channel) are also included.
    - If no sensor data is available but battery info exists, only battery-related data is added
      under "battery_data" (omitting sensor-specific fields).
    - Returns None if neither is available
    """
    try:
        logger.info("🔍 Extracting common fields from uplink message.")
        # Extract common fields that are always relevant
        extracted_data = {
            "timestamp": uplink_message.get("time", "N/A"),
            "device_eui": uplink_message.get("deviceInfo", {}).get("devEui", "N/A"),
            "device_name": uplink_message.get("deviceInfo", {}).get("deviceName", "N/A"),
            "region": uplink_message.get("deviceInfo", {}).get("tags", {}).get("region_name", "unknown"),
        }

        # Attempt to extract sensor data
        sensor_data = extract_sensor_data(uplink_message)
        battery_data = extract_battery_info(uplink_message)

        if sensor_data:
            extracted_data["sensor_data"] = sensor_data
            # Include sensor-specific fields only if sensor data is present
            extracted_data["gatewayId"] = uplink_message.get("rxInfo", [{}])[0].get("gatewayId", "N/A")
            extracted_data["rssi"] = uplink_message.get("rxInfo", [{}])[0].get("rssi", "N/A")
            extracted_data["snr"] = uplink_message.get("rxInfo", [{}])[0].get("snr", "N/A")
            extracted_data["frequency"] = uplink_message.get("txInfo", {}).get("frequency", "N/A")
            extracted_data["channel"] = uplink_message.get("rxInfo", [{}])[0].get("channel", "N/A")
        elif battery_data:
            # For battery messages, include only battery-related info.
            extracted_data["battery_data"] = battery_data
        else:
            logger.info("Ignoring message: No sensor or battery data provided.")
            return None

        logger.info(f"✅ Extracted relevant fields: {extracted_data}")
        return extracted_data

    except Exception as e:
        logger.error(f"❌ Error extracting relevant data: {e}")
        return None


def add_metadata(processed_data, fog_node_id):
    """
    Adds metadata (processed_by and processing_time) to the processed data.
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
        return processed_data
