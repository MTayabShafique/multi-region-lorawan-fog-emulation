import os

class BrokerDiscovery:
    def __init__(self, config_path=None):
        self.config_path = config_path

    def get_brokers(self):
        return [{
            "address": os.getenv("MQTT_BROKER", "haproxy"),
            "port": int(os.getenv("MQTT_PORT", 1883))
        }]
