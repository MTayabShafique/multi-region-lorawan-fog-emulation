import time
import logging
import threading
import json
from databases.influxdb.influxdb_converter import InfluxDBConverter
from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS

logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)

class InfluxDBWriter(threading.Thread):
    def __init__(self, name, event, queue, config):
        super().__init__()
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config

        logger.debug(f"Complete configuration passed to InfluxDBWriter: {self.config}")

        self.influxdb_url = f"http://{self.config.get('ip', '127.0.0.1')}:{self.config.get('port', 8086)}"
        self.influxdb_token = self.config.get("token")
        self.influxdb_org = self.config.get("org")
        self.influxdb_bucket = self.config.get("bucket")
        self.influxdb_measurements = self.config.get("measurements")

        logger.debug(f"InfluxDB Config - URL: {self.influxdb_url}, Token: {self.influxdb_token}, Org: {self.influxdb_org}, Bucket: {self.influxdb_bucket}, Measurements: {self.influxdb_measurements}")

        if not self.influxdb_token or not self.influxdb_org or not self.influxdb_bucket:
            logger.error("InfluxDB configuration is incomplete. Ensure 'token', 'org', and 'bucket' are specified.")
            raise ValueError("InfluxDB configuration is incomplete.")

        try:
            self.influx_client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            self.write_api = self.influx_client.write_api(write_options=SYNCHRONOUS)
            logger.info(f"{self.name} initialized successfully.")
        except Exception as e:
            logger.error(f"Error initializing InfluxDB client: {e}")
            raise

    def write_to_influxdb(self, influx_data):
        """Write formatted data to InfluxDB."""
        try:
            logger.debug(f"Writing data to InfluxDB: {influx_data.to_line_protocol()}")
            self.write_api.write(
                bucket=self.influxdb_bucket,
                org=self.influxdb_org,
                record=influx_data
            )
            logger.info(f"Data written to InfluxDB successfully: {influx_data.to_line_protocol()}")
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")

    def run(self):
        logger.info(f"Started {self.name}")

        while not self.event.is_set():
            try:
                if not self.queue.empty():
                    payload = self.queue.get()
                    logger.debug(f"Fetched payload from Memcached: {payload}")

                    # Convert payload from JSON string to dictionary if needed
                    if isinstance(payload, str):
                        try:
                            payload = json.loads(payload)
                            logger.debug(f"Converted JSON string to dictionary: {payload}")
                        except json.JSONDecodeError:
                            logger.error(f"Error decoding JSON payload: {payload}")
                            continue

                    influx_data = InfluxDBConverter.convert_to_influxdb_format(payload)
                    if influx_data:
                        logger.debug(f"Converted payload to InfluxDB format: {influx_data.to_line_protocol()}")
                        self.write_to_influxdb(influx_data)
                    else:
                        logger.warning("Conversion returned no data")
                else:
                    time.sleep(0.5)
                    logger.debug("Queue is empty, waiting for data...")
            except Exception as e:
                logger.error(f"Error processing data for InfluxDB: {e}")

        logger.info(f"Stopped: {self.name}")
