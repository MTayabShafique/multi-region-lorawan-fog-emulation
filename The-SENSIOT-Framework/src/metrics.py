from prometheus_client import Counter, Summary, Histogram, Gauge

# ---------------------------
# Prometheus Metrics Definitions
# ---------------------------
# Counter for every successfully received message, labeled by region and device_id
received_counter = Counter(
    'sensiot_received_messages_total',
    'Total number of received messages in SENSIOT',
    ['region', 'device_id']
)

# Counter for every dropped message (e.g., decoding errors), labeled by region and device_id
dropped_counter = Counter(
    'sensiot_dropped_messages_total',
    'Total number of dropped messages in SENSIOT',
    ['region', 'device_id']
)
