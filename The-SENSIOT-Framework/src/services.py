import logging
import os
from multiprocessing import Queue
from utilities.mqtt.mqtt_reader import MqttReader
from sensiot_memcache.memcache_reader import MemcacheReader
from sensiot_memcache.memcache_writer import MemcacheWriter
from databases.influxdb.influxdb_writer import InfluxDBWriter
from databases.prometheus.prometheus_writer import PrometheusWriter
from web.web import Web

logger = logging.LoggerAdapter(logging.getLogger("sensiot"), {"class": os.path.basename(__file__)})

class Services:
    def __init__(self, config, event):
        self.config = config
        self.event = event

        logger.debug(f"Loaded services configuration: {self.config.get('services')}")
        required_services = ["mqtt", "memcached", "influxdb_writer", "prometheus_writer"]
        for service in required_services:
            service_config = self.config.get("services", {}).get(service, None)
            if not service_config:
                raise ValueError(f"Missing or invalid configuration for service: {service}")

        self.services = {
            "influxdb_writer": self.__create_influxdb,
            "prometheus_writer": self.__create_prometheus,
            "web": self.__create_web,
            "sensor_data_memcache_writer": self.__create_sensor_data_memcache,
        }

    def get_services(self, service_type):
        logger.debug(f"Requested service type: {service_type}")
        if service_type not in self.services:
            raise ValueError(f"Unknown service type: {service_type}")
        try:
            return self.services[service_type]()
        except Exception as e:
            logger.error(f"Failed to initialize service '{service_type}': {e}")
            raise

    def __create_sensor_data_memcache(self):
        try:
            threads = []

            queue_size = self.config.get("queue_size", 10)
            sensor_data_queue = Queue(maxsize=queue_size)

            mqtt_reader = MqttReader(
                "SensorData_Memcache_MqttReader",
                self.event,
                sensor_data_queue,
                self.config["services"]["mqtt"],
            )
            memcache_writer = MemcacheWriter(
                "SensorData_Memcache_Writer",
                self.event,
                sensor_data_queue,
                self.config["services"]["memcached"],
            )

            threads.extend([mqtt_reader, memcache_writer])
            logger.info("Sensor Data Memcache Writer service initialized successfully.")
            return threads
        except Exception as e:
            logger.error(f"Error initializing Sensor Data Memcache Writer: {e}")
            raise

    def __create_influxdb(self):
        try:
            threads = []

            queue_size = self.config.get("queue_size", 10)
            influxdb_queue = Queue(maxsize=queue_size)

            memcache_reader = MemcacheReader(
                "InfluxDB_MemcacheReader",
                self.event,
                influxdb_queue,
                self.config['services']['memcached'],
            )
            influxdb_writer = InfluxDBWriter(
                "InfluxDB_Writer",
                self.event,
                influxdb_queue,
                self.config['services']['influxdb_writer'],
            )

            threads.extend([memcache_reader, influxdb_writer])
            logger.info("InfluxDB Writer service initialized successfully.")
            return threads
        except Exception as e:
            logger.error(f"Error initializing InfluxDB Writer: {e}")
            raise

    def __create_prometheus(self):
        try:
            threads = []

            queue_size = self.config.get("queue_size", 10)
            prometheus_queue = Queue(maxsize=queue_size)

            memcache_reader = MemcacheReader(
                "Prometheus_MemcacheReader",
                self.event,
                prometheus_queue,
                self.config['services']['memcached'],
            )
            prometheus_writer = PrometheusWriter(
                "Prometheus_Writer",
                self.event,
                prometheus_queue,
                self.config['services']['prometheus_writer'],
            )

            threads.extend([memcache_reader, prometheus_writer])
            logger.info("Prometheus Writer service initialized successfully.")
            return threads
        except Exception as e:
            logger.error(f"Error initializing Prometheus Writer: {e}")
            raise

    def __create_web(self):
        try:
            web = Web("Web", self.event, self.config)
            logger.info("Web service initialized successfully.")
            return [web]
        except Exception as e:
            logger.error(f"Error initializing Web service: {e}")
            raise
