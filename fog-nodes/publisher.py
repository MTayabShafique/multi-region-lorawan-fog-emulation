# publisher.py
import json

def publish_to_central(mqtt_client, data):
    """
    Publish aggregated data to the central topic via MQTT.
    """
    payload_str = json.dumps(data)
    ret = mqtt_client.publish(data.get("central_topic", "central/data"), payload_str)
    if ret.rc != 0:
        raise Exception(f"MQTT publish failed with return code: {ret.rc}")
    return ret
