#influxdb_client.py
from influxdb import InfluxDBClient

client = InfluxDBClient('localhost', 8086, 'root', 'root', 'lorawan')

def write_metrics(metrics, timestamp):
    json_body = [{
        "measurement": "uplink_metrics",
        "tags": {"device": metrics["device"], "region": metrics["region"]},
        "time": timestamp,
        "fields": metrics
    }]
    client.write_points(json_body)