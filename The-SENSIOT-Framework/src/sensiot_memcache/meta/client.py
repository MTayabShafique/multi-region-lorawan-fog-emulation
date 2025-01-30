import json
import logging
import os

from pymemcache.client.base import Client as PymemcacheClient


logger = logging.LoggerAdapter(logging.getLogger("sensiot"), {"class": os.path.basename(__file__)})

class Client:
    def __init__(self, config):
        self.config = config
        self.memcache_client = PymemcacheClient(server=(self.config["ip"], self.config["port"]), serializer=self.json_serializer, deserializer=self.json_deserializer, connect_timeout=self.config["connect_timeout"], timeout=self.config["timeout"])

    def json_serializer(self, key, value):
        if type(value) == str:
            return value, 1
        return json.dumps(value), 2

    def json_deserializer(self, key, value, flags):
        if flags == 1:
            return value
        if flags == 2:
            return json.loads(value)
        raise Exception("Unknown serialization format")

    def write(self, key, message):
        logger.info("Writing to cache: {}".format(key))
        self.memcache_client.set(key,
                                 message,
                                 expire=self.config["key_expiration"],
                                 noreply=self.config["noreply_flag"])

    def read(self, key):
        logger.info("Reading from cache: {}".format(key))
        return self.memcache_client.get(key)
