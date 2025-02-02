from flask_restful import Resource

class SensorList(Resource):
    def __init__(self, memcache_client):
        super(SensorList, self).__init__()
        self.memcache_client = memcache_client

    def get(self, prefix):
        try:
            key = f"{prefix}sensorlist"
            data = self.memcache_client.read(key)
            if data:
                return {"status": "success", "data": data}, 200
            else:
                return {"status": "error", "message": "Sensor list not found"}, 404
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
