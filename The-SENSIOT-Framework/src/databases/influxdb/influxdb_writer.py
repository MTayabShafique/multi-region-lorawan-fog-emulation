import logging
import threading
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Initialize the logger
logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)

class InfluxDBWriter(threading.Thread):
    def __init__(self, name, event, queue, config):
        super().__init__()
        self.name = name
        self.event = event
        self.queue = queue
        self.config = config

        # Debugging: Log the entire configuration passed
        logger.debug(f"Complete configuration passed to InfluxDBWriter: {self.config}")

        # Directly use self.config to extract the keys
        self.influxdb_url = f"http://{self.config.get('ip', '127.0.0.1')}:{self.config.get('port', 8086)}"
        self.influxdb_token = self.config.get("token")
        self.influxdb_org = self.config.get("org")
        self.influxdb_bucket = self.config.get("bucket")

        # Debug the extracted configuration
        logger.debug(f"InfluxDB Config - URL: {self.influxdb_url}, Token: {self.influxdb_token}, "
                     f"Org: {self.influxdb_org}, Bucket: {self.influxdb_bucket}")

        # Validate the configuration
        if not self.influxdb_token or not self.influxdb_org or not self.influxdb_bucket:
            logger.error("InfluxDB configuration is incomplete. Ensure 'token', 'org', and 'bucket' are specified.")
            raise ValueError("InfluxDB configuration is incomplete.")

        # Initialize the InfluxDB client
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
            logger.debug(f"Writing data to InfluxDB: {influx_data}")
            self.write_api.write(
                bucket=self.influxdb_bucket,
                org=self.influxdb_org,
                record=influx_data
            )
            logger.info(f"Data written to InfluxDB successfully: {influx_data}")
        except Exception as e:
            logger.error(f"Error writing to InfluxDB: {e}")

    def run(self):
        logger.info(f"Started {self.name}")

        while not self.event.is_set():
            try:
                if not self.queue.empty():
                    payload = self.queue.get()
                    logger.debug(f"Retrieved payload from queue: {payload}")
                    influx_data = self.convert_to_influxdb_format(payload)
                    if influx_data:
                        logger.debug(f"Converted payload to InfluxDB format: {influx_data}")
                        self.write_to_influxdb(influx_data)
                    else:
                        logger.warning("Conversion returned no data")
                else:
                    logger.debug("Queue is empty, waiting for data...")
            except Exception as e:
                logger.error(f"Error processing data for InfluxDB: {e}")

        logger.info(f"Stopped: {self.name}")

    def convert_to_influxdb_format(self, payload):
        """Convert payload to InfluxDB Point format."""
        try:
            logger.debug(f"Converting payload: {payload}")
            decoded_payload = payload.get("decodedPayload", "")

            # Debug decoded payload
            logger.debug(f"Decoded payload: {decoded_payload}")

            fields = {
                "temperature": float(decoded_payload.split(",")[1].split(":")[1].strip()),
                "humidity": float(decoded_payload.split(",")[0].split(":")[1].strip())
            }

            # Debug extracted fields
            logger.debug(f"Extracted fields - Temperature: {fields['temperature']}, Humidity: {fields['humidity']}")

            # Create an InfluxDB Point
            point = Point("sensor_data") \
                .tag("device_eui", payload.get("devEUI")) \
                .field("temperature", fields["temperature"]) \
                .field("humidity", fields["humidity"]) \
                .time(payload.get("timestamp"))  # Optional timestamp

            return point
        except Exception as e:
            logger.error(f"Failed to convert payload to InfluxDB format: {e}")
            return None
