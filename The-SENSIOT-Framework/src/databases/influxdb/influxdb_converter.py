import json
import logging
from influxdb_client import Point

logger = logging.getLogger("sensiot")
logger.setLevel(logging.DEBUG)

class InfluxDBConverter:
    @staticmethod
    def convert_to_influxdb_format(payload):
        """Convert enriched payload with sensor data to an InfluxDB Point for 'sensor_data'."""
        try:
            logger.debug(f"Converting payload for sensor data: {payload}")

            sensor_data = payload.get("sensor_data")
            if not sensor_data:
                logger.warning("No sensor_data found in payload; skipping sensor point conversion.")
                return None

            # Extract sensor fields with defaults if missing
            temperature = float(sensor_data.get("temperature", 0))
            humidity = float(sensor_data.get("humidity", 0))

            gateway_id = payload.get("gatewayId", "unknown")

            # Convert additional fields with proper type conversion
            rssi = payload.get("rssi")
            if rssi not in [None, "N/A"]:
                try:
                    rssi = int(rssi)
                except ValueError:
                    rssi = None

            snr = payload.get("snr")
            if snr not in [None, "N/A"]:
                try:
                    snr = float(snr)
                except ValueError:
                    snr = None

            frequency = payload.get("frequency")
            if frequency not in [None, "N/A"]:
                try:
                    frequency = int(frequency)
                except ValueError:
                    frequency = None

            raw_channel = payload.get("rxInfo", [{}])[0].get("channel", None)
            channel = None
            if raw_channel not in [None, "N/A"]:
                try:
                    channel = int(raw_channel)
                except ValueError:
                    channel = None

            logger.debug(f"Extracted sensor fields - Temperature: {temperature}, Humidity: {humidity}")

            point = (
                Point("sensor_data")
                .tag("device_eui", payload.get("device_eui", "unknown"))
                .tag("device_name", payload.get("device_name", "unknown"))
                .tag("region", payload.get("region", "unknown"))
                .tag("gatewayId", gateway_id)
                .field("temperature", temperature)
                .field("humidity", humidity)
            )

            if rssi is not None:
                point.field("rssi", rssi)
            if snr is not None:
                point.field("snr", snr)
            if frequency is not None:
                point.field("frequency", frequency)
            if channel is not None:
                point.field("channel", channel)

            point.time(payload.get("timestamp"))
            logger.debug(f"Created InfluxDB sensor_data point: {point.to_line_protocol()}")
            return point
        except Exception as e:
            logger.error(f"Failed to convert payload to InfluxDB sensor_data format: {e}")
            return None

    @staticmethod
    def convert_battery_to_influxdb_format(payload):
        """Convert enriched payload with battery data to an InfluxDB Point for 'battery_status'."""
        try:
            logger.debug(f"Converting payload for battery data: {payload}")
            battery_data = payload.get("battery_data")
            if not battery_data:
                logger.warning("No battery_data found in payload; skipping battery point conversion.")
                return None

            point = (
                Point("battery_status")
                .tag("device_eui", payload.get("device_eui", "unknown"))
                .tag("device_name", payload.get("device_name", "unknown"))
                .tag("region", payload.get("region", "unknown"))
                .time(payload.get("timestamp"))
            )

            if "batteryLevel" in battery_data:
                try:
                    point.field("batteryLevel", float(battery_data["batteryLevel"]))
                except ValueError:
                    logger.warning("Battery level value is not numeric.")
            if "margin" in battery_data:
                try:
                    point.field("margin", float(battery_data["margin"]))
                except ValueError:
                    logger.warning("Margin value is not numeric.")
            if "externalPowerSource" in battery_data:
                point.field("externalPowerSource", 1 if battery_data["externalPowerSource"] else 0)
            if "batteryLevelUnavailable" in battery_data:
                point.field("batteryLevelUnavailable", 1 if battery_data["batteryLevelUnavailable"] else 0)

            logger.debug(f"Created InfluxDB battery_status point: {point.to_line_protocol()}")
            return point
        except Exception as e:
            logger.error(f"Failed to convert payload to InfluxDB battery_status format: {e}")
            return None
