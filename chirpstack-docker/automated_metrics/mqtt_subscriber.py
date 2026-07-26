import os
import ssl
import paho.mqtt.client as mqtt
import json
import base64
from airtime_calculator import calculate_airtime
from energy_calculator import calculate_energy
from latency_calculator import calculate_latency
from influx_writer import write_metrics
from region import extract_region

# Load environment variables for MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "haproxy")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "application/+/device/+/event/up")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("Connected to MQTT broker", flush=True)
        client.subscribe(MQTT_TOPIC)
    else:
        print("Failed to connect, return code =", reason_code, flush=True)

def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload)
        device = data["deviceInfo"].get("deviceName", "unknown-device")
        region = extract_region(data)
        tx_info = data.get("txInfo", {}).get("modulation", {}).get("lora", {})
        sf = tx_info.get("spreadingFactor", 7)
        bw = tx_info.get("bandwidth", 125000)
        timestamp = data.get("time")

        # Decode payload
        encoded_payload = data.get("data", "")
        payload_bytes = base64.b64decode(encoded_payload)
        payload_size = len(payload_bytes)

        # Calculate metrics
        airtime = calculate_airtime(payload_size, sf, bw)
        energy = calculate_energy(airtime)
        latency = calculate_latency(timestamp)

        metrics = {
            "device": device,
            "region": region,
            "sf": sf,
            "payload_size": payload_size,
            "airtime_ms": airtime * 1000,
            "energy_mJ": energy * 1000,
            "latency_ms": latency
        }

        write_metrics(metrics, timestamp)
        print(f"Metrics for {device} written to InfluxDB: {metrics}")

    except Exception as e:
        print(f"Error processing message: {e}", flush=True)

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    if os.getenv("MQTT_TLS_ENABLED", "true").lower() in ("1", "true", "yes"):
        client.tls_set(
            ca_certs=os.environ["MQTT_TLS_CA"],
            certfile=os.environ["MQTT_TLS_CERT"],
            keyfile=os.environ["MQTT_TLS_KEY"],
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.tls_insecure_set(False)
    client.on_connect = on_connect
    client.on_message = on_message

    client.reconnect_delay_set(min_delay=1, max_delay=60)
    client.connect_async(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever(retry_first_connection=True)

if __name__ == "__main__":
    main()
