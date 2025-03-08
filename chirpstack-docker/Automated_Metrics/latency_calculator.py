#latency_calculator.py
from datetime import datetime
from dateutil import parser

def calculate_latency(chirpstack_time_str):
    # Replace this line with actual simulator sent time extraction
    simulator_time = datetime.utcnow()
    chirpstack_time = parser.parse(chirpstack_time_str)
    latency = (chirpstack_time - simulator_time).total_seconds() * 1000
    return abs(latency)  # Return latency in milliseconds