from datetime import datetime
from dateutil import parser
import pytz  # Ensure pytz is installed

def calculate_latency(chirpstack_time_str):
    """
    Calculate the latency between the ChirpStack received time and the current time.
    """
    # Parse the ChirpStack timestamp (which may have timezone info)
    chirpstack_time = parser.parse(chirpstack_time_str)

    # Ensure UTC timezone for ChirpStack time
    if chirpstack_time.tzinfo is None:
        chirpstack_time = chirpstack_time.replace(tzinfo=pytz.UTC)

    # Get the current UTC time with timezone
    simulator_time = datetime.utcnow().replace(tzinfo=pytz.UTC)

    # Calculate latency in milliseconds
    latency = (chirpstack_time - simulator_time).total_seconds() * 1000
    return abs(latency)  # Ensure latency is positive
