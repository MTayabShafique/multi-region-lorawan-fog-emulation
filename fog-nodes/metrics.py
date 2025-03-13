from prometheus_client import Counter, Summary, Histogram, Gauge

# Prometheus metrics definitions with labels for region and device_id
received_counter = Counter(
    'received_messages',
    'Total number of received messages',
    ['region', 'device_id']
)
dropped_counter = Counter(
    'dropped_messages',
    'Total number of dropped messages',
    ['region', 'device_id']
)
forwarded_counter = Counter(
    'forwarded_messages',
    'Total number of forwarded messages',
    ['region', 'device_id']
)
events_detected_counter = Counter(
    'events_detected',
    'Total number of sensor events detected',
    ['region', 'device_id']
)

latency_summary = Summary(
    'chirpstack_fog_latency_seconds',
    'ChirpStack to Fog Node latency',
    ['region', 'device_id']
)
latency_histogram = Histogram(
    'chirpstack_fog_latency_seconds_hist',
    'ChirpStack to Fog Node latency histogram',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    labelnames=['region', 'device_id']
)

avg_temperature_gauge = Gauge(
    'avg_temperature_per_window',
    'Average temperature per time window',
    ['region', 'device_id']
)

buffer_queue_length = Gauge('buffer_queue_length', 'Current length of the buffer queue')
