import os
import json
import logging
import paho.mqtt.client as mqtt
from data_processors.data_processor import extract_relevant_data, add_metadata

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REGION = os.getenv("FOG_REGION", "unknown")
BROKER_ADDRESS = os.getenv("MQTT_BROKER", "mqtt")
BROKER_PORT = int(os.getenv("MQTT_PORT", 1883))
PUBLISH_TOPIC = f"fog/{REGION}/processed"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"✅ Connected to MQTT broker on fog node {REGION}")
        topic = f"fog/{REGION}/process"
        client.subscribe(topic, qos=1)
        logger.info(f"🔗 Subscribed to topic {topic}")
    else:
        logger.error(f"❌ Connection failed with code {rc}")

def on_message(client, userdata, msg):
    payload_str = msg.payload.decode('utf-8')
    logger.info(f"📩 Received message on topic {msg.topic}: {payload_str}")

    try:
        uplink_message = json.loads(payload_str)
    except json.JSONDecodeError:
        logger.error("❌ Error: Received non-JSON payload.")
        return

    processed_data = extract_relevant_data(uplink_message)
    if processed_data is None:
        logger.info("Message ignored due to lack of valid sensor or battery data.")
        return

    enriched_data = add_metadata(processed_data, f"fog_node_{REGION}")
    logger.info(f"📝 Processed Data (before publishing): {json.dumps(enriched_data, indent=2)}")
    client.publish(PUBLISH_TOPIC, json.dumps(enriched_data), qos=1)
    logger.info(f"🚀 Published processed data to {PUBLISH_TOPIC}")

def start_fog_node_mqtt():
    client = mqtt.Client(client_id=f"fog_node_{REGION}_subscriber", userdata={"region": REGION})
    client.on_connect = on_connect
    client.on_message = on_message

    retries = 0
    max_retries = 10
    while retries < max_retries:
        try:
            logger.info(f"🔌 Attempting connection to {BROKER_ADDRESS}:{BROKER_PORT} (Attempt {retries+1})")
            client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
            break
        except Exception as e:
            logger.error(f"❌ Connection attempt {retries+1} failed: {e}")
            retries += 1
    else:
        logger.critical("❌ Max retries reached. Could not connect to MQTT broker.")
        return

    client.loop_forever()

if __name__ == "__main__":
    start_fog_node_mqtt()
