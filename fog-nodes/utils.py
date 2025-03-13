from datetime import datetime

def parse_iso_timestamp(ts_str):
    """
    Parse an ISO 8601 timestamp, truncating fractional seconds to 6 digits if necessary.
    Example: "2025-03-12T00:42:32.195186478+00:00" becomes "2025-03-12T00:42:32.195186+00:00"
    """
    try:
        if '.' in ts_str:
            date_part, frac_and_tz = ts_str.split('.', 1)
            tz_index = None
            for sep in ['+', '-']:
                idx = frac_and_tz.find(sep)
                if idx != -1:
                    tz_index = idx
                    break
            if tz_index is not None:
                frac_part = frac_and_tz[:tz_index]
                tz_part = frac_and_tz[tz_index:]
            else:
                frac_part = frac_and_tz
                tz_part = ""
            frac_fixed = (frac_part + "000000")[:6]
            ts_fixed = f"{date_part}.{frac_fixed}{tz_part}"
            return datetime.fromisoformat(ts_fixed)
        else:
            return datetime.fromisoformat(ts_str)
    except Exception as e:
        raise ValueError(f"Error parsing timestamp {ts_str}: {e}")

def is_valid_payload(payload):
    """
    Validate that required sensor data exists and is within acceptable ranges.
    If the keys "temperature" and "humidity" are not present at the top level,
    then look for them inside the "object" field.
    """
    try:
        sensor_data = payload.get("object", payload)
        temp = sensor_data.get("temperature")
        hum = sensor_data.get("humidity")
        if temp is None or hum is None:
            return False
        temp = float(temp)
        hum = float(hum)
        return -50 <= temp <= 100 and 0 <= hum <= 100
    except Exception:
        return False
