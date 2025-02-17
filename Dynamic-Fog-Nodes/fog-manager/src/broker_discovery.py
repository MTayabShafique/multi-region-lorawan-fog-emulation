import json

class BrokerDiscovery:
    def __init__(self, config_path):
        self.config_path = config_path

    def get_brokers(self):
        with open(self.config_path, 'r') as f:
            data = json.load(f)
        return data.get("brokers", [])
