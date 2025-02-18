import threading
import time
import paho.mqtt.client as mqtt
import importlib
from src.broker_discovery import BrokerDiscovery


def handle_message(client, userdata, msg):
    try:
        # Use a relative import to load message_processor lazily
        message_processor = importlib.import_module("src.message_processor")
    except Exception as e:
        print("Error importing message_processor:", e)
        return
    # Now call the on_message function from message_processor.
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
            for client in self.active_clients.values():
                client.disconnect()

    def monitor_brokers(self):
        while self.running:
            brokers = self.discovery.get_brokers()
            with self.lock:
                # Create a new client for each broker if not already created.
                for broker in brokers:
                    region = broker.get("region")
                    if region not in self.active_clients:
                        print(f"Connecting to broker for region: {region}")
                        client = self.create_client(broker)
                        self.active_clients[region] = client
                    else:
                        print(f"✅ Broker already connected for region: {region}, skipping re-subscription.")
            time.sleep(10)

    def create_client(self, broker):
        client = mqtt.Client(client_id=f"client_{broker.get('region')}")
        client.on_message = handle_message
        client.connect(broker.get("address"), broker.get("port"), 60)
        if not client.is_connected():
            print(f"📡 Subscribing to application/# for {broker.get('region')}")
            client.subscribe("application/#")
        threading.Thread(target=client.loop_forever, daemon=True).start()
        return client
