# influxdb_converter.py
import logging
from datetime import datetime, timezone
from influxdb_client import Point

logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)


class InfluxDBConverter:
    @staticmethod
    def convert_to_influxdb_format(payload):
        """
        Convert an aggregated payload to an InfluxDB Point.
        Expects keys: device_id, device_name, region, avg_temperature, avg_humidity, timestamp, and event.
        If the timestamp is numeric (epoch), it is converted to an ISO8601 string in UTC.
        If the timestamp is a string that does not include 'T' as the separator, it replaces the first space with 'T'.
        """
        try:
            ts = payload.get("timestamp")
            if isinstance(ts, (int, float)):
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                ts_iso = dt.isoformat()
            elif isinstance(ts, str):
                ts = ts.strip()  # remove any trailing whitespace
                # If the string uses a space between date and time, replace it with 'T'
                if 'T' not in ts:
                    ts = ts.replace(' ', 'T', 1)
                try:
                    dt = datetime.fromisoformat(ts)
                except Exception as e:
                    logger.error(f"fromisoformat failed for timestamp '{ts}': {e}")
                    # Fallback: try interpreting the string as an epoch float
                    dt = datetime.utcfromtimestamp(float(ts))
                ts_iso = dt.replace(tzinfo=timezone.utc).isoformat()
            else:
                raise ValueError("Timestamp format not recognized")

            temperature = float(payload.get("avg_temperature", 0))
            avg_humidity = float(payload.get("avg_humidity", 0))

            point = (
                Point("aggregated_sensors_data_v2")
                .tag("device_id", payload.get("device_id", "unknown"))
                .tag("device_name", payload.get("device_name", "unknown"))
                .tag("region", payload.get("region", "unknown"))
                .field("avg_temperature", temperature)
                .field("avg_humidity", avg_humidity)
                .field("event", 1 if payload.get("event") else 0)
            )
            point.time(ts_iso)
            logger.debug(f"Created InfluxDB point: {point.to_line_protocol()}")
            return point
        except Exception as e:
            logger.error(f"Failed to convert payload to InfluxDB format: {e}")
            return None
