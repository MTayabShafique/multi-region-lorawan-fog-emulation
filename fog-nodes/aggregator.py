import time
import json
import threading
import queue
import logging
from statistics import mean
from metrics import forwarded_counter, avg_temperature_gauge, dropped_counter
from datetime import datetime
from publisher import publish_to_central


logger = logging.getLogger(__name__)

# Aggregator structure: keyed by device id
aggregator = {}
aggregator_lock = threading.Lock()

def update_aggregator(device_id, device_name, region, temperature, humidity, event_detected):
    """
    Update aggregator with sensor readings.
    """
    with aggregator_lock:
        if device_id not in aggregator:
            aggregator[device_id] = {
                "temps": [],
                "humidities": [],
                "device_name": device_name,
                "region": region,
                "event": False
            }
        aggregator[device_id]["temps"].append(temperature)
        aggregator[device_id]["humidities"].append(humidity)
        if event_detected:
            aggregator[device_id]["event"] = True

def aggregation_worker(mqtt_client, aggregation_interval, metrics):
    """
    Periodically compute per-device aggregates, publish aggregated data, and clear the aggregator.
    """
    while True:
        time.sleep(aggregation_interval)
        aggregated_messages = []
        with aggregator_lock:
            for device_id, data in aggregator.items():
                if data["temps"]:
                    avg_temp = mean(data["temps"])
                    avg_hum = mean(data["humidities"]) if data["humidities"] else None
                    avg_temperature_gauge.labels(region=data["region"], device_id=device_id).set(avg_temp)
                    aggregated_data = {
                        "device_id": device_id,
                        "device_name": data["device_name"],
                        "region": data["region"],
                        "avg_temperature": avg_temp,
                        "avg_humidity": avg_hum,
                        "timestamp": time.time(),
                        "event": data["event"]
                    }
                    aggregated_messages.append(aggregated_data)
                    logger.info(f"Aggregated data for device {device_id}: {aggregated_data}")
            aggregator.clear()

        # Publish aggregated messages
        for msg in aggregated_messages:
            try:
                publish_to_central(mqtt_client, msg)
                logger.info(f"Forwarded aggregated data to central: {msg}")
            except Exception as e:
                logger.error(f"Failed to publish aggregated message: {msg} - {e}")
                dropped_counter.labels(region=msg["region"], device_id=msg["device_id"]).inc()
