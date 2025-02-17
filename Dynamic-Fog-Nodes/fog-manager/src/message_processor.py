import json
from src.fog_container_manager import fog_manager

def on_message(client, userdata, msg):
    topic = msg.topic
    payload_str = msg.payload.decode('utf-8')
    try:
        payload = json.loads(payload_str)
    except Exception as e:
        print(f"Error parsing payload: {e}. Raw payload: {payload_str}")
        return

    # Extract the region from the payload's 'regionConfigId' field.
    region = payload.get("regionConfigId")
    if not region:
        print(f"regionConfigId not found in payload: {payload_str}")
        return

    print(f"Received message for region {region}: {topic} -> {payload_str}")
    fog_manager.route_message(region, payload_str)
