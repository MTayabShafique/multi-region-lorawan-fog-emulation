import os
import json
import time
import threading
import queue
from statistics import mean
from datetime import datetime
import paho.mqtt.client as mqtt

# Configuration via environment variables
REGION = os.getenv("REGION", "us915_0")
MQTT_BROKER = os.getenv("MQTT_BROKER", "chirpstack-docker_haproxy_1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
CENTRAL_TOPIC = os.getenv("CENTRAL_TOPIC", "central/data")
FOG_SUB_TOPIC = f"region/{REGION}/#"
AGGREGATION_INTERVAL = int(os.getenv("AGGREGATION_INTERVAL", "150"))  # seconds

# Thresholds for validation and event detection (example values)
TEMPERATURE_NOISE_THRESHOLD = 0.5  # noise range around baseline
TEMPERATURE_EVENT_THRESHOLD = 35   # trigger event if temperature > 35
HUMIDITY_EVENT_THRESHOLD = 80       # trigger event if humidity > 80

# Metrics storage (in-memory counters)
metrics = {
    "received": 0,
    "dropped": 0,
    "forwarded": 0,
    "latency_measurements": []
}

# Local buffer queue for messages to be forwarded to central server
buffer_queue = queue.Queue()

# In-memory aggregator: sensor_id -> list of values within aggregation window
aggregator = {}

# Lock for thread-safe metrics update
metrics_lock = threading.Lock()


def is_valid_payload(payload):
    """Validate that required fields exist and are within acceptable ranges."""
    try:
        if "temperature" not in payload or "humidity" not in payload:
            return False
        # Check simple numeric types
        temp = float(payload["temperature"])
        hum = float(payload["humidity"])
        # If values are unrealistically negative or high, drop them.
        if not (-50 <= temp <= 100 and 0 <= hum <= 100):
            return False
        return True
    except Exception:
        return False


def process_message(payload, topic):
    """Process incoming message: validation, latency measurement, aggregation, event detection."""
    now = time.time()
    metrics_update("received")

    # Measure end-to-end latency if message contains a timestamp (epoch seconds in float)
    if "ts" in payload:
        try:
            msg_ts = float(payload["ts"])  # assume ts is in seconds
            latency = now - msg_ts
            with metrics_lock:
                metrics["latency_measurements"].append(latency)
            print(f"[{REGION}] Latency: {latency:.3f} seconds")
        except Exception:
            pass

    if not is_valid_payload(payload):
        print(f"[{REGION}] Dropping invalid payload: {payload}")
        metrics_update("dropped")
        return

    # Noise filtering example: if temperature change is minimal (you can enhance this logic)
    sensor_id = payload.get("device_id", "unknown")
    temp = float(payload["temperature"])
    # Initialize aggregator if not present
    if sensor_id not in aggregator:
        aggregator[sensor_id] = []
    aggregator[sensor_id].append(temp)

    # Event detection: if current reading exceeds a threshold, mark as event
    event_detected = False
    if temp > TEMPERATURE_EVENT_THRESHOLD or float(payload["humidity"]) > HUMIDITY_EVENT_THRESHOLD:
        event_detected = True
        print(f"[{REGION}] Event detected for sensor {sensor_id}: {payload}")

    # Build minimal data to forward: aggregation or event data.
    aggregated_data = {
        "device_id": sensor_id,
        "avg_temperature": mean(aggregator[sensor_id]),
        "humidity": payload["humidity"],
        "timestamp": now,
        "event": event_detected
    }

    # Place data in local buffer for forwarding
    buffer_queue.put(aggregated_data)
    metrics_update("forwarded")


def metrics_update(metric_name):
    """Update metrics counter in a thread-safe way."""
    with metrics_lock:
        metrics[metric_name] += 1


def aggregation_worker():
    """Periodically clear the aggregator after aggregation interval."""
    while True:
        time.sleep(AGGREGATION_INTERVAL)
        with metrics_lock:
            print(f"[{REGION}] Aggregated metrics: {metrics}")
        # For simplicity, clear the aggregator after each interval.
        aggregator.clear()


def forward_worker(mqtt_client):
    """Continuously try to forward buffered messages to the central server."""
    while True:
        try:
            data = buffer_queue.get(timeout=1)
            # Publish to central topic via MQTT
            payload_str = json.dumps(data)
            ret = mqtt_client.publish(CENTRAL_TOPIC, payload_str)
            if ret.rc != mqtt.MQTT_ERR_SUCCESS:
                print(f"[{REGION}] Failed to publish, re-buffering message: {data}")
                buffer_queue.put(data)  # re-buffer
            else:
                print(f"[{REGION}] Forwarded data to central: {data}")
            buffer_queue.task_done()
        except queue.Empty:
            time.sleep(1)
        except Exception as e:
            print(f"[{REGION}] Exception in forward worker: {e}")
            time.sleep(1)


# Updated MQTT Callbacks for Paho MQTT v2.0
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[{REGION}] Connected to MQTT broker with result code {rc}")
    client.subscribe(FOG_SUB_TOPIC)
    print(f"[{REGION}] Subscribed to topic: {FOG_SUB_TOPIC}")


def on_message(client, userdata, msg):
    print(f"[{REGION}] Received raw message on topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        print(f"[{REGION}] Parsed payload: {payload}")
        process_message(payload, msg.topic)
    except Exception as e:
        print(f"[{REGION}] Error processing message: {e}")


def setup_mqtt_client(client_id):
    # No callback_api_version parameter here; we use the new API.
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main():
    # Setup MQTT client for subscription (fog ingestion) and for central forwarding
    client = setup_mqtt_client(f"fog_node_{REGION}")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start aggregator and forward worker threads
    threading.Thread(target=aggregation_worker, daemon=True).start()
    threading.Thread(target=forward_worker, args=(client,), daemon=True).start()

    # Start MQTT loop (blocking call)
    client.loop_forever()


if __name__ == "__main__":
    main()
