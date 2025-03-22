import json
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from utils import parse_iso_timestamp
from processing import process_message
from metrics import received_counter, latency_summary, latency_histogram, dropped_counter
from collections import defaultdict


if not logging.getLogger().hasHandlers():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')
    
logger = logging.getLogger(__name__)

uplink_counter = defaultdict(int)

def on_connect(client, userdata, flags, rc, properties=None):
    region = userdata.get("region")
    logger.info(f"[{region}] Connected to MQTT broker with result code {rc}")
    topic = userdata.get("fog_sub_topic")
    client.subscribe(topic)
    logger.info(f"[{region}] Subscribed to topic: {topic}")

def on_message(client, userdata, msg):
    region = userdata.get("region")
    uplink_counter[region] += 1
    logger.info(f"[{region}] Uplink count: {uplink_counter[region]}")
    logger.info(f"[{region}] Received raw message on topic: {msg.topic}")
    try:
        # Get the time when the fog node receives the message (offset-aware)
        received_at_fog = datetime.now(timezone.utc)
        # Instead of expecting an outer payload with an inner payload,
        # we assume the received JSON is the complete payload.
        payload = json.loads(msg.payload.decode())
        logger.info(f"[{region}] Parsed payload: {payload}")

        # Update received counter with device info (if available)
        device_info = payload.get("deviceInfo", {})
        device_id = device_info.get("devEui", "unknown")
        received_counter.labels(region=region, device_id=device_id).inc()

        # Calculate ChirpStack -> Fog Node latency using nsTime from rxInfo if present
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
        # Process the complete payload
        process_message(payload, msg.topic)
    except Exception as e:
        logger.error(f"[{region}] Error processing message: {e}")
        dropped_counter.labels(region=region, device_id="unknown").inc()

def setup_mqtt_client(client_id, region, fog_sub_topic):
    client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
    client.user_data_set({"region": region, "fog_sub_topic": fog_sub_topic})
    client.on_connect = on_connect
    client.on_message = on_message
    return client
