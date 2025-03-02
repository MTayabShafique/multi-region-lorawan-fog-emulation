import os
import json
import time
import logging
import paho.mqtt.client as mqtt
from data_processors.data_processor import extract_relevant_data, add_metadata

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Environment variables
REGION = os.getenv("FOG_REGION", "unknown")
BROKER_ADDRESS = os.getenv("MQTT_BROKER", "haproxy_fog")  # ✅ Ensure it's haproxy_fog
BROKER_PORT = int(os.getenv("MQTT_PORT", 1883))
PUBLISH_TOPIC = f"fog/{REGION}/processed"


def on_connect(client, userdata, flags, rc):
    """Callback when Fog Node connects to MQTT Broker"""
    if rc == 0:
        logger.info(f"✅ Connected to MQTT broker on fog node {REGION}")
        topic = f"fog/{REGION}/process"
        client.subscribe(topic, qos=1)
        logger.info(f"🔗 Subscribed to topic {topic}")
    else:
        logger.error(f"❌ Connection failed with code {rc}")


def on_message(client, userdata, msg):
    """Callback when Fog Node receives a message"""
    logger.info(f"🛠️ on_message triggered with topic: {msg.topic}")
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
    """Start MQTT connection with retries and exponential backoff"""
    client = mqtt.Client(client_id=f"fog_node_{REGION}_subscriber", userdata={"region": REGION})
    client.on_connect = on_connect
    client.on_message = on_message

    retries = 0
    max_retries = 10
    base_delay = 5  # Start with 2s delay, increases exponentially

    while retries < max_retries:
        try:
            logger.info(f"🔌 Attempting connection to {BROKER_ADDRESS}:{BROKER_PORT} (Attempt {retries + 1})")
            client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
            logger.info("✅ Connection successful!")
            break
        except Exception as e:
            logger.error(f"❌ Connection attempt {retries + 1} failed: {e}")
            retries += 1
            wait_time = base_delay ** retries  # Exponential backoff
            logger.info(f"⏳ Retrying in {wait_time} seconds...")
            time.sleep(wait_time)

    if retries == max_retries:
        logger.critical("❌ Max retries reached. Could not connect to MQTT broker. Exiting.")
        return

    client.loop_forever()


if __name__ == "__main__":
    start_fog_node_mqtt()
