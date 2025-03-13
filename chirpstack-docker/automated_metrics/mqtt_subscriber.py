import os
import paho.mqtt.client as mqtt
import json
import base64
from airtime_calculator import calculate_airtime
from energy_calculator import calculate_energy
from latency_calculator import calculate_latency
from influx_writer import write_metrics

# Load environment variables for MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "haproxy")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "application/+/device/+/event/up")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC)
    else:
        print("Failed to connect, return code =", rc)

def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload)
        device = data["deviceInfo"].get("deviceName", "unknown-device")
        region = data.get("deviceInfo", {}).get("tags", {}).get("region_name", "unknown-region")
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
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
