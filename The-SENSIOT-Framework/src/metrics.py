from prometheus_client import Counter, Summary, Histogram, Gauge

# Total number of messages received, labeled by region and device_id
received_counter = Counter(
    'received_messages_total',
    'Total number of received messages',
    ['region', 'device_id']
)

# Total number of messages dropped, labeled by region and device_id
dropped_counter = Counter(
    'dropped_messages_total',
    'Total number of dropped messages',
    ['region', 'device_id']
)

# Total number of messages forwarded, labeled by region and device_id
forwarded_counter = Counter(
    'forwarded_messages_total',
    'Total number of forwarded messages',
    ['region', 'device_id']
)

# Total number of sensor events detected (if applicable), labeled by region and device_id
events_detected_counter = Counter(
    'events_detected_total',
    'Total number of sensor events detected',
    ['region', 'device_id']
)

# Summary for latency from ChirpStack to Fog Node (in seconds)
latency_summary = Summary(
    'chirpstack_fog_latency_seconds',
    'Latency from ChirpStack to Fog Node in seconds',
    ['region', 'device_id']
)

# Histogram for latency with defined buckets (in seconds)
latency_histogram = Histogram(
    'chirpstack_fog_latency_seconds_histogram',
    'Histogram of ChirpStack to Fog Node latency in seconds',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    labelnames=['region', 'device_id']
)

