import json
import time
import logging
from statistics import mean
from utils import is_valid_payload, parse_iso_timestamp
from metrics import received_counter, dropped_counter, forwarded_counter, events_detected_counter, latency_summary, \
    latency_histogram
from aggregator import update_aggregator

logger = logging.getLogger(__name__)


def process_message(payload, topic):
    """
        Process inner payload:
          - Validate sensor data.
          - Extract device information.
          - Aggregate sensor data.
          - Detect events.
    """
    # Extract device info for metrics labeling
    device_info = payload.get("deviceInfo", {})
    device_id = device_info.get("devEui", "unknown")
    device_name = device_info.get("deviceName", "unknown")
    region_from_config = payload.get("regionConfigId", "unknown")

    if not is_valid_payload(payload):
        logger.warning(f"Dropping invalid payload: {payload}")
        dropped_counter.labels(region=region_from_config, device_id=device_id).inc()
        return

    # Prefer sensor data from the "object" field if present
    sensor_data = payload.get("object", payload)
    try:
        temperature = float(sensor_data.get("temperature"))
        humidity = float(sensor_data.get("humidity", 0))
    except Exception as e:
        logger.error(f"Error converting sensor values: {sensor_data} - {e}")
        dropped_counter.labels(region=region_from_config, device_id=device_id).inc()
        return

    # Determine if event is detected
    event_detected = (temperature > 35 or humidity > 80)
    if event_detected:
        events_detected_counter.labels(region=region_from_config, device_id=device_id).inc()
        logger.info(f"Event detected for sensor {device_name} (ID: {device_id}): {sensor_data}")

    # Update aggregator for this device
    update_aggregator(device_id, device_name, region_from_config, temperature, humidity, event_detected)
    forwarded_counter.labels(region=region_from_config, device_id=device_id).inc()


def publish_to_central(mqtt_client, data):
    """
    Publish aggregated data to the central topic via MQTT.
    """
    payload_str = json.dumps(data)
    ret = mqtt_client.publish(data.get("central_topic", "central/data"), payload_str)
    if ret.rc != 0:
        raise Exception(f"MQTT publish failed with return code: {ret.rc}")
    return ret
