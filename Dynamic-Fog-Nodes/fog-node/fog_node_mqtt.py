# fog_node_mqtt.py
import time
import os
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker on fog node")
        region = userdata.get("region", "unknown")
        topic = f"fog/{region}/process"
        client.subscribe(topic, qos=1)
        print(f"Subscribed to topic {topic}")
    else:
        print(f"Connection failed with code {rc}")

def on_message(client, userdata, msg):
    message = msg.payload.decode('utf-8')
    print(f"Fog node received message on topic {msg.topic}: {message}")
    # You can integrate further logic here (e.g., storing the data or calling your /process endpoint).

def start_fog_node_mqtt():
    region = os.getenv("FOG_REGION", "unknown")
    broker_address = os.getenv("MQTT_BROKER", "mqtt")
    broker_port = int(os.getenv("MQTT_PORT", 1883))  # Default to 1883

    client = mqtt.Client(client_id=f"fog_node_{region}_subscriber", userdata={"region": region})
    client.on_connect = on_connect
    client.on_message = on_message

    # Implement retry logic
    retries = 0
    max_retries = 5
    while retries < max_retries:
        try:
            print(f"Attempting connection to {broker_address}:{broker_port} (attempt {retries+1})")
            client.connect(broker_address, broker_port, 60)
            break  # Connection successful, exit loop
        except ConnectionRefusedError as e:
            print(f"Connection attempt {retries+1} failed: {e}. Retrying in 3 seconds...")
            retries += 1
            time.sleep(3)
    else:
        print("Max retries reached. Could not connect to MQTT broker.")
        return

    client.loop_forever()

if __name__ == "__main__":
    start_fog_node_mqtt()
