import logging
import os
import re
import time

from prometheus_client import start_http_server

from autoscaler_metrics import (
    current_replicas,
    decisions,
    desired_replicas,
    errors,
    observed_message_rate,
    observed_outbox_backlog,
)
from clients import DockerServiceClient, PrometheusClient
from policy import ScalingDecisionEngine, ScalingPolicy


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="[%(asctime)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def env_int(name, default):
    return int(os.getenv(name, str(default)))


def env_float(name, default):
    return float(os.getenv(name, str(default)))


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_region_services(value, stack_name):
    result = {}
    for item in value.split(","):
        region, service = (part.strip() for part in item.split(":", 1))
        if not re.fullmatch(r"[a-z0-9_]+", region):
            raise ValueError(f"Invalid region name: {region!r}")
        full_service_name = (
            service if service.startswith(f"{stack_name}_") else f"{stack_name}_{service}"
        )
        result[region] = full_service_name
    if not result:
        raise ValueError("At least one region service is required")
    return result


def build_policy():
    return ScalingPolicy(
        minimum_replicas=env_int("MIN_REPLICAS", 2),
        maximum_replicas=env_int("MAX_REPLICAS", 8),
        target_messages_per_second=env_float(
            "TARGET_MESSAGES_PER_SECOND_PER_REPLICA", 20
        ),
        scale_down_utilization=env_float("SCALE_DOWN_UTILIZATION", 0.5),
        backlog_scale_up_threshold=env_int("BACKLOG_SCALE_UP_THRESHOLD", 10),
        scale_up_periods=env_int("SCALE_UP_PERIODS", 2),
        scale_down_periods=env_int("SCALE_DOWN_PERIODS", 5),
        scale_up_step=env_int("SCALE_UP_STEP", 2),
        scale_down_step=env_int("SCALE_DOWN_STEP", 1),
        cooldown_seconds=env_int("COOLDOWN_SECONDS", 120),
    )


def main():
    stack_name = os.getenv("STACK_NAME", "sensiot-fog")
    region_services = parse_region_services(
        os.getenv(
            "REGION_SERVICES",
            "eu868:fog-node-eu868,us915_0:fog-node-us915,"
            "in865:fog-node-in865,ru864:fog-node-ru864",
        ),
        stack_name,
    )
    interval = env_float("EVALUATION_INTERVAL_SECONDS", 30)
    rate_window = os.getenv("RATE_WINDOW", "2m")
    if not re.fullmatch(r"[1-9][0-9]*[smhdwy]", rate_window):
        raise ValueError(f"Invalid Prometheus RATE_WINDOW: {rate_window!r}")
    dry_run = env_bool("AUTOSCALER_DRY_RUN", True)
    metrics_port = env_int("METRICS_PORT", 8010)

    prometheus = PrometheusClient(os.getenv("PROMETHEUS_URL", "http://prometheus:9090"))
    docker = DockerServiceClient(
        os.getenv("DOCKER_API_URL", "http://docker-socket-proxy:2375"),
        stack_name,
        region_services.values(),
    )
    engine = ScalingDecisionEngine(build_policy())

    start_http_server(metrics_port)
    logger.info(
        "Fog autoscaler started: dry_run=%s interval=%ss regions=%s",
        dry_run,
        interval,
        ",".join(region_services),
    )

    while True:
        cycle_started = time.monotonic()
        for region, service_name in region_services.items():
            try:
                replicas = docker.current_replicas(service_name)
            except Exception:
                errors.labels(region=region, source="docker_read").inc()
                logger.exception("[%s] Could not read service %s", region, service_name)
                continue

            try:
                message_rate = prometheus.regional_message_rate(region, rate_window)
                backlog = prometheus.regional_outbox_backlog(region)
            except Exception:
                errors.labels(region=region, source="prometheus").inc()
                logger.exception("[%s] Could not read Prometheus signals", region)
                continue

            decision = engine.evaluate(
                region,
                replicas,
                message_rate,
                backlog,
                time.monotonic(),
            )
            observed_message_rate.labels(region=region).set(message_rate)
            observed_outbox_backlog.labels(region=region).set(backlog)
            current_replicas.labels(region=region).set(replicas)
            desired_replicas.labels(region=region).set(decision.desired_replicas)
            decisions.labels(
                region=region,
                action=decision.action,
                reason=decision.reason,
            ).inc()

            logger.info(
                "[%s] rate=%.3f/s backlog=%.0f replicas=%d desired=%d "
                "action=%s reason=%s",
                region,
                message_rate,
                backlog,
                replicas,
                decision.desired_replicas,
                decision.action,
                decision.reason,
            )
            if decision.desired_replicas == replicas or dry_run:
                continue
            try:
                docker.scale_service(service_name, decision.desired_replicas)
                engine.record_successful_scale(region, time.monotonic())
            except Exception:
                errors.labels(region=region, source="docker_update").inc()
                logger.exception("[%s] Failed to scale %s", region, service_name)

        elapsed = time.monotonic() - cycle_started
        time.sleep(max(interval - elapsed, 1))


if __name__ == "__main__":
    main()
