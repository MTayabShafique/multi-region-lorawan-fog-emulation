#mqtt_subscriber.py
import paho.mqtt.client as mqtt
import json
import base64
from influxdb_client import write_metrics
from airtime_calculator import calculate_airtime
from energy_calculator import calculate_energy
from latency_calculator import calculate_latency

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "application/+/device/+/event/up"

def on_message(client, userdata, message):
    data = json.loads(message.payload)
    device = data["deviceInfo"]["deviceName"]
    region = data["deviceInfo"]["region_name"]
    sf = data["txInfo"]["modulation"]["lora"]["spreadingFactor"]
    bw = data["txInfo"]["modulation"]["lora"]["bandwidth"]
    timestamp = data["time"]

    payload = base64.b64decode(data["data"])
    payload_size = len(payload)

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

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
mqtt_client.subscribe(MQTT_TOPIC)
mqtt_client.loop_forever()