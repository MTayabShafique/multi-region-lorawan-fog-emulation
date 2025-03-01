import json
import logging
import os
from src import globals as g

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set to keep track of processed messages to avoid duplicates.
processed_messages = set()

def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode("utf-8")
    logger.info(f"📥 Received message on topic: {topic} -> {payload_str}")

    try:
        uplink_data = json.loads(payload_str)
        message_id = uplink_data.get("deduplicationId")
        if message_id and message_id in processed_messages:
            logger.warning(f"⚠️ Duplicate message {message_id} ignored.")
            return
        if message_id:
            processed_messages.add(message_id)

        # Extract region from the uplink message.
        region = uplink_data.get("deviceInfo", {}).get("tags", {}).get("region_name")
        if not region:
            region = os.getenv("DEFAULT_REGION", "unknown_region")
        logger.info(f"🌍 Routing message to region: {region}")

        if g.fog_manager:
            g.fog_manager.route_message(region, payload_str)
        else:
            logger.error("Fog manager instance not set. Cannot route message.")
    except json.JSONDecodeError:
        logger.error("❌ Error decoding JSON payload.")
    except Exception as e:
        logger.error(f"❌ Unexpected error processing message: {e}")
