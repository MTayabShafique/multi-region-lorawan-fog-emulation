import logging

logger = logging.getLogger("battery_processor")
logger.setLevel(logging.INFO)

def extract_battery_info(uplink_message):
    """
    Extracts battery-related information from the uplink message.
    Looks for keys such as 'batteryLevel', 'margin', 'externalPowerSource', and 'batteryLevelUnavailable'.
    Returns a dictionary with battery info if present, otherwise None.
    """
    battery_keys = ["batteryLevel", "margin", "externalPowerSource", "batteryLevelUnavailable"]
    battery_info = {}
    for key in battery_keys:
        if key in uplink_message:
            battery_info[key] = uplink_message[key]
    if battery_info:
        return battery_info
    return None
