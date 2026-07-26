# publisher.py
import json
import paho.mqtt.client as mqtt

def publish_to_central(
    mqtt_client,
    data,
    central_topic="central/data",
    publish_timeout=10,
):
    """
    Publish aggregated data at QoS 1 and wait for the broker acknowledgment.
    """
    payload_str = json.dumps(data)
    ret = mqtt_client.publish(central_topic, payload_str, qos=1)
    if ret.rc != mqtt.MQTT_ERR_SUCCESS:
        raise Exception(f"MQTT publish failed with return code: {ret.rc}")
    ret.wait_for_publish(timeout=publish_timeout)
    if not ret.is_published():
        raise TimeoutError(
            f"MQTT broker did not acknowledge publish within {publish_timeout} seconds"
        )
    return ret
