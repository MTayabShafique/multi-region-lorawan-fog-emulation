import copy
import unittest

from clients import DockerServiceClient, PrometheusClient


class FakeResponse:
    def __init__(self, body, status_code=200):
        self.body = body
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return copy.deepcopy(self.body)


class FakeSession:
    def __init__(self, get_responses=None, post_response=None):
        self.get_responses = list(get_responses or [])
        self.post_response = post_response or FakeResponse({})
        self.get_calls = []
        self.post_calls = []

    def get(self, url, **kwargs):
        self.get_calls.append((url, kwargs))
        return self.get_responses.pop(0)

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return self.post_response


def service_payload(name="sensiot-fog_fog-node-eu868", replicas=2):
    return {
        "ID": "service-id",
        "Version": {"Index": 42},
        "Spec": {
            "Name": name,
            "Labels": {"com.docker.stack.namespace": "sensiot-fog"},
            "Mode": {"Replicated": {"Replicas": replicas}},
            "TaskTemplate": {"ContainerSpec": {"Image": "fog@test"}},
        },
    }


class PrometheusClientTests(unittest.TestCase):
    def test_query_scalar_reads_single_vector_value(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "status": "success",
                        "data": {
                            "result": [
                                {"metric": {}, "value": [1000, "12.5"]}
                            ]
                        },
                    }
                )
            ]
        )
        client = PrometheusClient("http://prometheus:9090", session=session)

        self.assertEqual(client.regional_message_rate("eu868", "2m"), 12.5)
        self.assertIn('region="eu868"', session.get_calls[0][1]["params"]["query"])

    def test_query_rejects_ambiguous_results(self):
        session = FakeSession(
            [
                FakeResponse(
                    {
                        "status": "success",
                        "data": {"result": [{}, {}]},
                    }
                )
            ]
        )
        client = PrometheusClient("http://prometheus:9090", session=session)

        with self.assertRaises(RuntimeError):
            client.query_scalar("up")


class DockerServiceClientTests(unittest.TestCase):
    def setUp(self):
        self.service_name = "sensiot-fog_fog-node-eu868"

    def test_scale_preserves_spec_and_updates_only_replica_count(self):
        session = FakeSession(
            [FakeResponse(service_payload())],
            FakeResponse({}),
        )
        client = DockerServiceClient(
            "http://proxy:2375",
            "sensiot-fog",
            [self.service_name],
            session=session,
        )

        client.scale_service(self.service_name, 4)

        _, call = session.post_calls[0]
        self.assertEqual(call["params"]["version"], 42)
        self.assertEqual(call["json"]["Mode"]["Replicated"]["Replicas"], 4)
        self.assertEqual(
            call["json"]["TaskTemplate"]["ContainerSpec"]["Image"], "fog@test"
        )

    def test_disallowed_service_is_rejected_before_http_request(self):
        session = FakeSession()
        client = DockerServiceClient(
            "http://proxy:2375",
            "sensiot-fog",
            [self.service_name],
            session=session,
        )

        with self.assertRaises(PermissionError):
            client.get_service("unrelated_service")
        self.assertEqual(session.get_calls, [])

    def test_wrong_stack_label_is_rejected(self):
        payload = service_payload()
        payload["Spec"]["Labels"]["com.docker.stack.namespace"] = "other"
        session = FakeSession([FakeResponse(payload)])
        client = DockerServiceClient(
            "http://proxy:2375",
            "sensiot-fog",
            [self.service_name],
            session=session,
        )

        with self.assertRaises(PermissionError):
            client.get_service(self.service_name)

    def test_scaling_waits_for_existing_update(self):
        payload = service_payload()
        payload["UpdateStatus"] = {"State": "updating"}
        session = FakeSession([FakeResponse(payload)])
        client = DockerServiceClient(
            "http://proxy:2375",
            "sensiot-fog",
            [self.service_name],
            session=session,
        )

        with self.assertRaises(RuntimeError):
            client.scale_service(self.service_name, 4)


if __name__ == "__main__":
    unittest.main()
