import time
import json
import threading
import logging
from statistics import mean
from datetime import datetime
from metrics import forwarded_counter, avg_temperature_gauge, dropped_counter
from publisher import publish_to_central
from collections import defaultdict

logger = logging.getLogger(__name__)

# Aggregator structure: keyed by device id
aggregator = {}
aggregator_lock = threading.Lock()

# Local in-memory counter for published aggregated messages per region
local_published_counter = defaultdict(int)

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

import time
import json
import threading
import logging
from statistics import mean
from datetime import datetime
from metrics import forwarded_counter, avg_temperature_gauge, dropped_counter
from publisher import publish_to_central
from collections import defaultdict

logger = logging.getLogger(__name__)

# Aggregator structure: keyed by device id
aggregator = {}
aggregator_lock = threading.Lock()

# Local in-memory counter for published aggregated messages per region
local_published_counter = defaultdict(int)

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
    Periodically compute per-device aggregates, publish aggregated data, update metrics,
    log forwarded messages, and clear the aggregator.
    
    This version waits the full aggregation_interval BEFORE the first run,
    preventing a run at t=0.
    """
    # Delay the first run until aggregation_interval has passed.
    # This ensures only ONE run if the entire simulation also lasts exactly aggregation_interval.
    logger.info(f"Aggregator worker started, will first run after {aggregation_interval} seconds.")
    time.sleep(aggregation_interval)
    
    while True:
        aggregated_messages = []
        with aggregator_lock:
            for device_id, data in aggregator.items():
                if data["temps"]:
                    avg_temp = mean(data["temps"])
                    avg_hum = mean(data["humidities"]) if data["humidities"] else None
                    # Update the Prometheus gauge for average temperature
                    avg_temperature_gauge.labels(region=data["region"], device_id=device_id).set(avg_temp)
                    
                    aggregated_data = {
                        "device_id": device_id,
                        "device_name": data["device_name"],
                        "region": data["region"],
                        "avg_temperature": avg_temp,
                        "avg_humidity": avg_hum,
                        "timestamp": datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S %Z'),
                        "event": data["event"]
                    }
                    aggregated_messages.append(aggregated_data)
                    logger.info(f"Aggregated data for device {device_id}: {aggregated_data}")
            # Clear the aggregator after processing all devices
            aggregator.clear()

        # Publish aggregated messages
        for msg in aggregated_messages:
            try:
                publish_to_central(mqtt_client, msg)
                # Increment the Prometheus forwarded counter for this aggregated message
                forwarded_counter.labels(region=msg["region"], device_id=msg["device_id"]).inc()
                
                # Update local published counter per region
                local_published_counter[msg["region"]] += 1
                
                logger.info(f"Forwarded aggregated data to central: {msg}")
                logger.info(f"[{msg['region']}] Total published aggregated messages: {local_published_counter[msg['region']]}")
            except Exception as e:
                logger.error(f"Failed to publish aggregated message: {msg} - {e}")
                dropped_counter.labels(region=msg["region"], device_id=msg["device_id"]).inc()
        
        # Wait again for the next cycle
        time.sleep(aggregation_interval)

