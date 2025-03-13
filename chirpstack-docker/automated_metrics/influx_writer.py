import os
from dateutil import parser
from influxdb_client import InfluxDBClient, Point, WriteOptions


# Environment variables for InfluxDB 2.x
INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "lorawan_org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "lorawan_bucket")

# Instantiate the InfluxDBClient
client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)

# Create a Write API (synchronous for simplicity)
write_api = client.write_api(write_options=WriteOptions(batch_size=1))


def write_metrics(metrics, timestamp_str):
    """
    Write the device metrics to InfluxDB 2.x using a Point structure.
    :param metrics: dict containing metric fields
    :param timestamp_str: string time from the uplink (e.g., 2025-03-08T19:28:12.600+00:00)
    """
    # Convert to datetime so we can set the InfluxDB point time
    try:
        timestamp_dt = parser.parse(timestamp_str)
    except Exception:
        # If parsing fails or timestamp is missing, fallback to no explicit time
        timestamp_dt = None

    point = (
        Point("uplink_metrics")
        .tag("device", metrics["device"])
        .tag("region", metrics["region"])
        .field("sf", metrics["sf"])
        .field("payload_size", metrics["payload_size"])
        .field("airtime_ms", metrics["airtime_ms"])
        .field("energy_mJ", metrics["energy_mJ"])
        .field("latency_ms", metrics["latency_ms"])
    )

    # Set the time on the point, if we parsed it
    if timestamp_dt:
        point = point.time(timestamp_dt)

    # Write the point to our InfluxDB bucket
    write_api.write(
        bucket=INFLUX_BUCKET,
        record=point
    )
