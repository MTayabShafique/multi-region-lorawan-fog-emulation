import time
import os
from src.broker_discovery import BrokerDiscovery
from src.mqtt_manager import MQTTManager
from src.fog_container_manager import FogContainerManager
from src.fog_mqtt_router import FogMQTTRouter

def main():
    print("🚀 Fog Manager initializing...")

    # Read environment variables for MQTT
    mqtt_broker = os.getenv("MQTT_BROKER", "mqtt")
    mqtt_port = int(os.getenv("MQTT_PORT", 1883))

    # Initialize the MQTT Router (Handles message publishing)
    mqtt_publisher = FogMQTTRouter()

    # Instantiate Fog Container Manager (Manages dynamic fog nodes)
    container_manager = FogContainerManager(
        image_name="myorg/fog-node:latest",
        mqtt_publisher=mqtt_publisher
    )

    # Instantiate Broker Discovery and MQTT Manager
    discovery = BrokerDiscovery(config_path='/app/config/brokers.json')
    mqtt_mgr = MQTTManager(discovery)

    print("✅ Fog Manager started.")

    # Start MQTT Manager for handling uplink messages
    mqtt_mgr.start()

    # 🔹 Test message routing to verify MQTT connectivity
    test_message = '{"data": "Hello from Fog Manager!"}'
    region = "us915_0"  # You can change this dynamically based on test cases
    print(f"📤 Sending test message to region {region}...")
    mqtt_publisher.route_message(region, test_message)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("🛑 Shutting down Fog Manager gracefully...")
        mqtt_mgr.stop()

if __name__ == "__main__":
    main()
