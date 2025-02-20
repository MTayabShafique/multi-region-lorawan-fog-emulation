import json
import logging
import os
from src.fog_container_manager import fog_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Maintain a set of processed message IDs to prevent duplicate processing
processed_messages = set()

def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode("utf-8")
    logger.info(f"📥 Received message on topic: {topic} -> {payload_str}")

    try:
        uplink_data = json.loads(payload_str)

        # Ensure message is only processed once
        message_id = uplink_data.get("deduplicationId")
        if message_id and message_id in processed_messages:
            logger.warning(f"⚠️ Duplicate message {message_id} ignored.")
            return

        if message_id:
            processed_messages.add(message_id)

        # Extract region name with a fallback from environment variables
        region = uplink_data.get("deviceInfo", {}).get("tags", {}).get("region_name", None)

        if not region:
            region = os.getenv("DEFAULT_REGION", "unknown_region")  # Fallback if missing

        logger.info(f"🌍 Routing message to region: {region}")
        fog_manager.route_message(region, payload_str)

    except json.JSONDecodeError:
        logger.error("❌ Error decoding JSON payload.")
    except Exception as e:
        logger.error(f"❌ Unexpected error processing message: {e}")
