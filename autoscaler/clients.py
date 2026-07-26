from urllib.parse import quote

import requests


class PrometheusClient:
    def __init__(self, base_url, timeout=5, session=None):
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.session = session or requests.Session()

    def query_scalar(self, query):
        response = self.session.get(
            f"{self.base_url}/api/v1/query",
            params={"query": query},
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "success":
            raise RuntimeError(f"Prometheus query failed: {body}")

        result = body.get("data", {}).get("result", [])
        if len(result) != 1:
            raise RuntimeError(
                f"Prometheus query must return exactly one series, got {len(result)}"
            )
        return float(result[0]["value"][1])

    def regional_message_rate(self, region, rate_window):
        query = (
            f'sum(rate(received_messages_total{{region="{region}"}}'
            f"[{rate_window}])) or vector(0)"
        )
        return self.query_scalar(query)

    def regional_outbox_backlog(self, region):
        query = f'max(fog_outbox_messages{{region="{region}"}}) or vector(0)'
        return self.query_scalar(query)


class DockerServiceClient:
    ACTIVE_UPDATE_STATES = {
        "updating",
        "paused",
        "rollback_started",
        "rollback_paused",
    }

    def __init__(
        self,
        base_url,
        stack_name,
        allowed_services,
        timeout=5,
        session=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.stack_name = stack_name
        self.allowed_services = frozenset(allowed_services)
        self.timeout = float(timeout)
        self.session = session or requests.Session()

    def _validate_service_name(self, service_name):
        if service_name not in self.allowed_services:
            raise PermissionError(
                f"Service {service_name!r} is not in the autoscaler allowlist"
            )

    def get_service(self, service_name):
        self._validate_service_name(service_name)
        response = self.session.get(
            f"{self.base_url}/services/{quote(service_name, safe='')}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        service = response.json()

        labels = service.get("Spec", {}).get("Labels", {})
        if labels.get("com.docker.stack.namespace") != self.stack_name:
            raise PermissionError(
                f"Service {service_name!r} does not belong to stack {self.stack_name!r}"
            )
        replicated = service.get("Spec", {}).get("Mode", {}).get("Replicated")
        if replicated is None or "Replicas" not in replicated:
            raise RuntimeError(f"Service {service_name!r} is not replicated")
        return service

    def current_replicas(self, service_name):
        service = self.get_service(service_name)
        return int(service["Spec"]["Mode"]["Replicated"]["Replicas"])

    def scale_service(self, service_name, desired_replicas):
        service = self.get_service(service_name)
        update_state = service.get("UpdateStatus", {}).get("State")
        if update_state in self.ACTIVE_UPDATE_STATES:
            raise RuntimeError(
                f"Service {service_name!r} is already in state {update_state!r}"
            )

        spec = service["Spec"]
        spec["Mode"]["Replicated"]["Replicas"] = int(desired_replicas)
        version = service["Version"]["Index"]
        response = self.session.post(
            f"{self.base_url}/services/{quote(service_name, safe='')}/update",
            params={"version": version},
            json=spec,
            timeout=self.timeout,
        )
        response.raise_for_status()
