import json
import logging
import os
import ssl
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from utils import get_secret, parse_iso_timestamp
from processing import process_message
from metrics import received_counter, latency_summary, latency_histogram, dropped_counter
from collections import defaultdict

# Set up logging if not already configured
if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Local in-memory counters (keyed by region)
uplink_counter = defaultdict(int)
local_dropped_counter = defaultdict(int)

def _normalize_region(region):
    return str(region or "").strip().lower()


def _extract_topic_region(topic):
    parts = topic.split("/")
    if len(parts) >= 2 and parts[0] == "region":
        return parts[1]
    return None


def _regions_match(expected_region, payload_region, topic_region):
    expected = _normalize_region(expected_region)
    payload = _normalize_region(payload_region)
    topic = _normalize_region(topic_region)
    return payload == expected and (not topic or topic == expected)


def on_connect(client, userdata, flags, rc, properties=None):
    region = userdata.get("region")
    if rc != 0:
        logger.error(f"[{region}] MQTT connection failed: {mqtt.connack_string(rc)}")
        return

    logger.info(f"[{region}] Connected to MQTT broker")
    topic = userdata.get("fog_sub_topic")
    result, mid = client.subscribe(topic, qos=1)
    if result != mqtt.MQTT_ERR_SUCCESS:
        logger.error(f"[{region}] Failed to subscribe to topic {topic}: MQTT result {result}")
        return
    logger.info(f"[{region}] Subscribed to topic at QoS 1: {topic} (mid={mid})")


def on_disconnect(client, userdata, rc, properties=None):
    region = userdata.get("region")
    if rc != 0:
        logger.warning(f"[{region}] Unexpected MQTT disconnect: {mqtt.error_string(rc)}")
    else:
        logger.info(f"[{region}] Disconnected from MQTT broker")


def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    region = userdata.get("region")
    if not granted_qos or any(qos == 128 for qos in granted_qos):
        logger.error(
            f"[{region}] Broker rejected MQTT subscription mid={mid}, "
            f"granted_qos={granted_qos}"
        )
        return
    logger.info(
        f"[{region}] Broker accepted MQTT subscription mid={mid}, "
        f"granted_qos={granted_qos}"
    )


def on_message(client, userdata, msg):
    region = userdata.get("region")
    logger.info(f"[{region}] Received raw message on topic: {msg.topic}")
    
    try:
        # Capture receive time and parse payload
        received_at_fog = datetime.now(timezone.utc)
        payload = json.loads(msg.payload.decode())

        # Update Prometheus received counter using device info (if available)
        device_info = payload.get("deviceInfo", {})
        device_id = device_info.get("devEui", "unknown")
        payload_region = payload.get("regionConfigId")
        topic_region = _extract_topic_region(msg.topic)

        if not _regions_match(region, payload_region, topic_region):
            logger.warning(
                f"[{region}] Dropping message with region mismatch: "
                f"payload_region={payload_region}, topic_region={topic_region}, topic={msg.topic}"
            )
            dropped_counter.labels(region=region, device_id=device_id).inc()
            local_dropped_counter[region] += 1
            return

        uplink_counter[region] += 1
        logger.info(f"[{region}] Uplink count: {uplink_counter[region]}")
        received_counter.labels(region=region, device_id=device_id).inc()

        # Calculate and log latency if available
        rx_info = payload.get("rxInfo", [{}])[0]
        ns_time_str = rx_info.get("nsTime")
        if ns_time_str:
            ns_time = parse_iso_timestamp(ns_time_str)
            chirpstack_fog_latency = (received_at_fog - ns_time).total_seconds()
            logger.info(f"[{region}] ChirpStack -> Fog Node Latency: {chirpstack_fog_latency:.3f} sec")
            latency_summary.labels(region=region, device_id=device_id).observe(chirpstack_fog_latency)
            latency_histogram.labels(region=region, device_id=device_id).observe(chirpstack_fog_latency)
        else:
            logger.warning(f"[{region}] nsTime missing in payload")

        # Hand off to further processing
        process_message(payload, msg.topic, region, userdata["aggregation_store"])

    except Exception as e:
        logger.error(f"[{region}] Error processing message: {e}")
        dropped_counter.labels(region=region, device_id="unknown").inc()
        local_dropped_counter[region] += 1
        logger.info(f"[{region}] Local dropped count: {local_dropped_counter[region]}")

def setup_mqtt_client(client_id, region, fog_sub_topic, aggregation_store):
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    username = os.getenv("MQTT_USERNAME")
    password = get_secret("MQTT_PASSWORD")
    if username and password:
        client.username_pw_set(username, password)
    if os.getenv("MQTT_TLS_ENABLED", "true").lower() in ("1", "true", "yes"):
        client.tls_set(
            ca_certs=os.environ["MQTT_TLS_CA"],
            certfile=os.environ["MQTT_TLS_CERT"],
            keyfile=os.environ["MQTT_TLS_KEY"],
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.tls_insecure_set(False)
    client.user_data_set(
        {
            "region": region,
            "fog_sub_topic": fog_sub_topic,
            "aggregation_store": aggregation_store,
        }
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)
    return client
