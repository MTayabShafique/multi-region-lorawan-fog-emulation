import json
import logging
from statistics import mean
from datetime import datetime
from utils import is_valid_payload
from metrics import dropped_counter, events_detected_counter
from aggregator import update_aggregator
from collections import defaultdict

logger = logging.getLogger(__name__)

# Local in-memory counter for dropped messages in processing (keyed by region)
local_dropped_counter_processing = defaultdict(int)

def process_message(payload, topic):
    """
    Process inner payload:
      - Validate sensor data.
      - Extract device information.
      - Aggregate sensor data.
      - Detect events.
      
    Note: Forwarded counter logic has been removed from this file.
    It will now only be updated in the aggregator worker when aggregated data is actually published.
    """
    # Extract device info for labeling
    device_info = payload.get("deviceInfo", {})
    device_id = device_info.get("devEui", "unknown")
    device_name = device_info.get("deviceName", "unknown")
    region_from_config = payload.get("regionConfigId", "unknown")

    # Validate payload; if invalid, update dropped counters
    if not is_valid_payload(payload):
        logger.warning(f"Dropping invalid payload: {payload}")
        dropped_counter.labels(region=region_from_config, device_id=device_id).inc()
        local_dropped_counter_processing[region_from_config] += 1
        logger.info(f"[{region_from_config}] Local dropped count in process_message: {local_dropped_counter_processing[region_from_config]}")
        return

    # Prefer sensor data from "object" field if available
    sensor_data = payload.get("object", payload)
    try:
        temperature = float(sensor_data.get("temperature"))
        humidity = float(sensor_data.get("humidity", 0))
    except Exception as e:
        logger.error(f"Error converting sensor values: {sensor_data} - {e}")
        dropped_counter.labels(region=region_from_config, device_id=device_id).inc()
        local_dropped_counter_processing[region_from_config] += 1
        logger.info(f"[{region_from_config}] Local dropped count in process_message: {local_dropped_counter_processing[region_from_config]}")
        return

    # Detect events based on thresholds
    event_detected = (temperature > 35 or humidity > 80)
    if event_detected:
        events_detected_counter.labels(region=region_from_config, device_id=device_id).inc()
        logger.info(f"Event detected for sensor {device_name} (ID: {device_id}): {sensor_data}")

    # Update aggregator for this device
    update_aggregator(device_id, device_name, region_from_config, temperature, humidity, event_detected)

