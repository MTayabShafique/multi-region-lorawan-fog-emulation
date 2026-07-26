from prometheus_client import Counter, Gauge


observed_message_rate = Gauge(
    "fog_autoscaler_observed_messages_per_second",
    "Regional MQTT message rate observed by the autoscaler",
    ["region"],
)
observed_outbox_backlog = Gauge(
    "fog_autoscaler_observed_outbox_messages",
    "Regional durable outbox backlog observed by the autoscaler",
    ["region"],
)
current_replicas = Gauge(
    "fog_autoscaler_current_replicas",
    "Current fog worker replicas",
    ["region"],
)
desired_replicas = Gauge(
    "fog_autoscaler_desired_replicas",
    "Fog worker replicas selected by the scaling policy",
    ["region"],
)
decisions = Counter(
    "fog_autoscaler_decisions",
    "Autoscaler decisions",
    ["region", "action", "reason"],
)
errors = Counter(
    "fog_autoscaler_errors",
    "Autoscaler errors",
    ["region", "source"],
)
