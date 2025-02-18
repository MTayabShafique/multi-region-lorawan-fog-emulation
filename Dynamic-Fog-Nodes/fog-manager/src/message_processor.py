# message_processor.py
import json
from src.fog_container_manager import fog_manager
processed_messages= set()

def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode('utf-8')
    print(f"Received message on topic: {topic} -> {payload_str}")

    try:
        uplink_data = json.loads(payload_str)

        # Ensure message is only processed once
        message_id = uplink_data.get("deduplicationId", None)
        if message_id in processed_messages:
            print(f"⚠️ Duplicate message {message_id} ignored.")
            return
        processed_messages.add(message_id)

        region = uplink_data.get("deviceInfo", {}).get("tags", {}).get("region_name", "unknown_region")
        fog_manager.route_message(region, payload_str)

    except json.JSONDecodeError:
        print("Error decoding JSON payload.")
    except Exception as e:
        print(f"Unexpected error processing message: {e}")
