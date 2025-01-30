import json


class Measurement:
    def __init__(self, id, type):
        self.data = {"sensor_id": id, "type": type, "measurements": []}

    def add(self, name, value, unit):
        self.data['measurements'].append({"name": name, "value": float(value), "unit": unit})

    def to_json(self):
        return json.dumps(self.data)

    def __str__(self):
        return self.to_json()
