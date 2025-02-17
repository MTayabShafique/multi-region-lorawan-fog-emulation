import time
from src.broker_discovery import BrokerDiscovery
from src.mqtt_manager import MQTTManager

def main():
    discovery = BrokerDiscovery(config_path='/app/config/brokers.json')
    mqtt_mgr = MQTTManager(discovery)
    mqtt_mgr.start()
    print("Fog Manager started.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down Fog Manager...")
        mqtt_mgr.stop()

if __name__ == "__main__":
    main()
