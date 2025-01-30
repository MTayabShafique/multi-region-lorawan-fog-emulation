from flask_restful import Resource

class SensorData(Resource):
    def __init__(self, memcache_client):
        super(SensorData, self).__init__()
        self.memcache_client = memcache_client

    def get(self, prefix, device_id, sensor, sensor_id):
        try:
            key = f"{prefix}{device_id}{sensor}{sensor_id}"
            data = self.memcache_client.read(key)
            if data:
                return {"status": "success", "data": data}, 200
            else:
                return {"status": "error", "message": "Data not found"}, 404
        except Exception as e:
            return {"status": "error", "message": str(e)}, 500
