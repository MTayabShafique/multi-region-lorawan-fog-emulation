import threading
import time
import logging
import paho.mqtt.client as mqtt
import importlib
from src.broker_discovery import BrokerDiscovery

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_message(client, userdata, msg):
    try:
        # Dynamically import message processor to avoid circular imports
        message_processor = importlib.import_module("src.message_processor")
    except Exception as e:
        logger.error(f"❌ Error importing message_processor: {e}")
        return

    # Process message using the imported function
    message_processor.on_message(client, userdata, msg)

class MQTTManager:
    def __init__(self, discovery: BrokerDiscovery):
        self.discovery = discovery
        self.active_clients = {}  # Mapping: region -> MQTT client
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        threading.Thread(target=self.monitor_brokers, daemon=True).start()

    def stop(self):
        self.running = False
        with self.lock:
            for region, client in self.active_clients.items():
                logger.info(f"🛑 Disconnecting from broker for region: {region}")
                client.disconnect()

    def monitor_brokers(self):
        while self.running:
            brokers = self.discovery.get_brokers()

            with self.lock:
                for broker in brokers:
                    region = broker.get("region")
                    address = broker.get("address", "").strip()
                    port = int(broker.get("port", 1883))

                    if not address:
                        logger.warning(f"⚠️ Skipping broker for region {region} - missing address.")
                        continue

                    if region not in self.active_clients:
                        logger.info(f"🔗 Connecting to broker for region: {region} at {address}:{port}")
                        client = self.create_client(region, address, port)
                        self.active_clients[region] = client
                    else:
                        logger.debug(f"✅ Broker already connected for region: {region}, skipping re-subscription.")

            time.sleep(10)  # Monitor brokers every 10 seconds

    def create_client(self, region, address, port):
        client = mqtt.Client(client_id=f"client_{region}")

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"📡 Connected to broker for region: {region}. Subscribing to application/#")
                client.subscribe("application/#")
            else:
                logger.error(f"❌ Connection failed for region {region} with rc={rc}")

        client.on_connect = on_connect
        client.on_message = handle_message

        try:
            logger.info(f"🛠️ Attempting connection to {address}:{port}")
            client.connect(address, port, keepalive=60)  # Keepalive prevents stale connections

            threading.Thread(target=client.loop_forever, daemon=True).start()
        except Exception as e:
            logger.error(f"❌ Error connecting to MQTT broker {address}:{port} - {e}")

        return client
