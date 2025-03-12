import os
import json
import time
import threading
import queue
from statistics import mean
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Configuration via environment variables
REGION = os.getenv("REGION", "us915_0")
MQTT_BROKER = os.getenv("MQTT_BROKER", "chirpstack-docker_haproxy_1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
CENTRAL_TOPIC = os.getenv("CENTRAL_TOPIC", "central/data")
FOG_SUB_TOPIC = f"region/{REGION}/#"
AGGREGATION_INTERVAL = int(os.getenv("AGGREGATION_INTERVAL", "150"))  # seconds

# Thresholds for event detection (example values)
TEMPERATURE_EVENT_THRESHOLD = 35   # trigger event if temperature > 35°C
HUMIDITY_EVENT_THRESHOLD = 80       # trigger event if humidity > 80%

# Metrics storage (in-memory counters)
metrics = {
    "received": 0,
    "dropped": 0,
    "forwarded": 0,
    "chirpstack_fog_latency_measurements": []  # ChirpStack -> Fog Node latency (using nsTime)
}

# Local buffer queue for messages to be forwarded to central server
buffer_queue = queue.Queue()

# In-memory aggregator: keyed by device id (devEui) -> list of temperature values
aggregator = {}

# Lock for thread-safe metrics update
metrics_lock = threading.Lock()


def parse_iso_timestamp(ts_str):
    """
    Parse an ISO 8601 timestamp, truncating fractional seconds to 6 digits if necessary.
    Example: "2025-03-12T00:42:32.195186478+00:00" becomes "2025-03-12T00:42:32.195186+00:00"
    """
    try:
        if '.' in ts_str:
            date_part, frac_and_tz = ts_str.split('.', 1)
            tz_index = None
            for sep in ['+', '-']:
                idx = frac_and_tz.find(sep)
                if idx != -1:
                    tz_index = idx
                    break
            if tz_index is not None:
                frac_part = frac_and_tz[:tz_index]
                tz_part = frac_and_tz[tz_index:]
            else:
                frac_part = frac_and_tz
                tz_part = ""
            frac_fixed = (frac_part + "000000")[:6]
            ts_fixed = f"{date_part}.{frac_fixed}{tz_part}"
            return datetime.fromisoformat(ts_fixed)
        else:
            return datetime.fromisoformat(ts_str)
    except Exception as e:
        raise ValueError(f"Error parsing timestamp {ts_str}: {e}")


def is_valid_payload(payload):
    """
    Validate that required sensor data exists and is within acceptable ranges.
    It first looks for 'temperature' and 'humidity' at the top level; if not found,
    it attempts to extract them from the 'object' field.
    """
    try:
        temp = payload.get("temperature")
        hum = payload.get("humidity")
        if temp is None or hum is None:
            obj = payload.get("object", {})
            temp = obj.get("temperature")
            hum = obj.get("humidity")
        if temp is None or hum is None:
            return False
        temp = float(temp)
        hum = float(hum)
        if not (-50 <= temp <= 100 and 0 <= hum <= 100):
            return False
        return True
    except Exception:
        return False


def process_message(payload, topic):
    """
    Process the inner payload:
      - Validate sensor data.
      - Extract device information (device id, device name, region from regionConfigId).
      - Aggregate temperature values.
      - Detect events.
      - Buffer aggregated data for forwarding.
    """
    # Validate sensor data (will look in top-level or within "object")
    if not is_valid_payload(payload):
        print(f"[{REGION}] Dropping invalid payload: {payload}")
        metrics_update("dropped")
        return

    # Extract sensor data: Prefer values in 'object' if available
    sensor_data = payload.get("object", payload)

    # Extract device information from deviceInfo section
    device_info = payload.get("deviceInfo", {})
    device_id = device_info.get("devEui", "unknown")
    device_name = device_info.get("deviceName", "unknown")
    region_from_config = payload.get("regionConfigId", "unknown")

    try:
        temp = float(sensor_data.get("temperature"))
    except Exception:
        print(f"[{REGION}] Cannot convert temperature: {sensor_data.get('temperature')}")
        metrics_update("dropped")
        return

    # Use device_id as the aggregator key
    with metrics_lock:
        if device_id not in aggregator:
            aggregator[device_id] = []
        aggregator[device_id].append(temp)

    event_detected = False
    try:
        if temp > TEMPERATURE_EVENT_THRESHOLD or float(sensor_data.get("humidity", 0)) > HUMIDITY_EVENT_THRESHOLD:
            event_detected = True
            print(f"[{REGION}] Event detected for sensor {device_name} (ID: {device_id}): {sensor_data}")
    except Exception as e:
        print(f"[{REGION}] Error in event detection: {e}")

    aggregated_data = {
        "device_id": device_id,
        "device_name": device_name,
        "region": region_from_config,
        "avg_temperature": mean(aggregator[device_id]),
        "humidity": sensor_data.get("humidity"),
        "timestamp": time.time(),
        "event": event_detected
    }
    buffer_queue.put(aggregated_data)
    metrics_update("forwarded")


def metrics_update(metric_name):
    with metrics_lock:
        metrics[metric_name] += 1


def aggregation_worker():
    """Periodically log and reset aggregated metrics."""
    while True:
        time.sleep(AGGREGATION_INTERVAL)
        with metrics_lock:
            if metrics["chirpstack_fog_latency_measurements"]:
                avg_chirpstack_fog = (sum(metrics["chirpstack_fog_latency_measurements"]) /
                                        len(metrics["chirpstack_fog_latency_measurements"]))
            else:
                avg_chirpstack_fog = 0.0
            print(f"[{REGION}] Aggregated metrics: {{'received': {metrics['received']}, "
                  f"'dropped': {metrics['dropped']}, 'forwarded': {metrics['forwarded']}, "
                  f"'avg_chirpstack_fog_latency': {avg_chirpstack_fog:.3f} sec}}")
            metrics["chirpstack_fog_latency_measurements"].clear()


def forward_worker(mqtt_client):
    """Continuously forward buffered messages to the central topic via MQTT."""
    while True:
        try:
            data = buffer_queue.get(timeout=1)
            payload_str = json.dumps(data)
            ret = mqtt_client.publish(CENTRAL_TOPIC, payload_str)
            if ret.rc != mqtt.MQTT_ERR_SUCCESS:
                print(f"[{REGION}] Failed to publish, re-buffering message: {data}")
                buffer_queue.put(data)
            else:
                print(f"[{REGION}] Forwarded data to central: {data}")
            buffer_queue.task_done()
        except queue.Empty:
            time.sleep(1)
        except Exception as e:
            print(f"[{REGION}] Exception in forward worker: {e}")
            time.sleep(1)


# MQTT Callbacks for Paho MQTT v2.0
def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[{REGION}] Connected to MQTT broker with result code {rc}")
    client.subscribe(FOG_SUB_TOPIC)
    print(f"[{REGION}] Subscribed to topic: {FOG_SUB_TOPIC}")


def on_message(client, userdata, msg):
    print(f"[{REGION}] Received raw message on topic: {msg.topic}")
    try:
        # Use an offset-aware timestamp for fog receipt
        received_at_fog = datetime.now(timezone.utc)
        outer_payload = json.loads(msg.payload.decode())
        print(f"[{REGION}] Parsed outer payload: {outer_payload}")
        inner_payload_str = outer_payload.get("payload")
        if not inner_payload_str:
            print(f"[{REGION}] No inner payload found, dropping message.")
            metrics_update("dropped")
            return
        inner_payload = json.loads(inner_payload_str)
        print(f"[{REGION}] Parsed inner payload: {inner_payload}")

        # Calculate ChirpStack -> Fog Node latency using nsTime from rxInfo
        rx_info = inner_payload.get("rxInfo", [{}])[0]
        ns_time_str = rx_info.get("nsTime")
        if ns_time_str:
            ns_time = parse_iso_timestamp(ns_time_str)
            chirpstack_fog_latency = (received_at_fog - ns_time).total_seconds()
            print(f"[{REGION}] ChirpStack -> Fog Node Latency: {chirpstack_fog_latency:.3f} sec")
            with metrics_lock:
                metrics["chirpstack_fog_latency_measurements"].append(chirpstack_fog_latency)
        else:
            print(f"[{REGION}] nsTime missing in inner payload")
        process_message(inner_payload, msg.topic)
    except Exception as e:
        print(f"[{REGION}] Error processing message: {e}")
        metrics_update("dropped")


def setup_mqtt_client(client_id):
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    return client


def main():
    client = setup_mqtt_client(f"fog_node_{REGION}")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    threading.Thread(target=aggregation_worker, daemon=True).start()
    threading.Thread(target=forward_worker, args=(client,), daemon=True).start()

    client.loop_forever()


if __name__ == "__main__":
    main()
