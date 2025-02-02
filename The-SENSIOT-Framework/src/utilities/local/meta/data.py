class SensorData:
    def __init__(self, devEUI, data):
        self.data = json.loads(data.replace("'", '"'))
        self.data.update({
            "devEUI": devEUI,
            "timestamp": int(time.time())
        })

    def to_json(self):
        return json.dumps(self.data)

    def __str__(self):
        return self.to_json()
