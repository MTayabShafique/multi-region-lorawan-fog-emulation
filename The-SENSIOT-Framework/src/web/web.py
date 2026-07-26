import hmac
import logging
import os
import threading

from flask import Flask, request
from flask_restful import Api
import memcache
from werkzeug.serving import make_server
from web.resources.sensor_data import SensorData
from web.resources.sensor_list import SensorList

logger = logging.LoggerAdapter(logging.getLogger("sensiot"), {"class": os.path.basename(__file__)})


class MemcacheWebClient:
    def __init__(self, config):
        host = config.get("ip", "memcached")
        port = int(config.get("port", 11211))
        self.client = memcache.Client([f"{host}:{port}"], debug=False)

    def read(self, key):
        return self.client.get(key)


class Web(threading.Thread):
    def __init__(self, name, event, config):
        super(Web, self).__init__()
        self.name = name
        self.event = event
        self.app = Flask(__name__)
        self.host = config["services"]["web"].get("host", "0.0.0.0")
        self.port = int(config["services"]["web"].get("port", 5000))
        self.api_key = os.getenv("SENSIOT_WEB_API_KEY")
        if not self.api_key:
            raise ValueError("SENSIOT_WEB_API_KEY is required for the Web service.")

        @self.app.before_request
        def authenticate_request():
            if request.path == "/health":
                return None
            provided_key = request.headers.get("X-API-Key", "")
            if not hmac.compare_digest(provided_key, self.api_key):
                return {"status": "error", "message": "Unauthorized"}, 401
            return None

        @self.app.get("/health")
        def health():
            return {"status": "ok"}, 200

        api = Api(self.app)

        # Initialize Memcache client
        if 'services' not in config or 'memcached' not in config['services']:
            raise KeyError("'memcached' configuration is missing in 'services' section.")

        memcache_client = MemcacheWebClient(config['services']['memcached'])

        # Add API resources
        api.add_resource(SensorData,
                         '/<string:prefix>/<string:device_id>/<string:sensor>/<string:sensor_id>',
                         resource_class_kwargs={"memcache_client": memcache_client})
        api.add_resource(SensorList,
                         '/<string:prefix>/sensorlist',
                         resource_class_kwargs={"memcache_client": memcache_client})
        logger.info(f"{self.name} initialized successfully.")

    def run(self):
        logger.info(f"Started {self.name}")
        server = None
        try:
            server = make_server(self.host, self.port, self.app, threaded=True)
            server.timeout = 1
            while not self.event.is_set():
                server.handle_request()
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
        finally:
            if server is not None:
                server.server_close()
            logger.info(f"Stopped {self.name}")
