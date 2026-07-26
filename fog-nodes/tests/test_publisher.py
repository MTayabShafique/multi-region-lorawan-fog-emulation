import unittest

import paho.mqtt.client as mqtt

from publisher import publish_to_central


class FakePublishInfo:
    def __init__(self, published=True, rc=mqtt.MQTT_ERR_SUCCESS):
        self.rc = rc
        self._published = published
        self.timeout = None

    def wait_for_publish(self, timeout):
        self.timeout = timeout

    def is_published(self):
        return self._published


class FakeMqttClient:
    def __init__(self, result):
        self.result = result
        self.call = None

    def publish(self, topic, payload, qos):
        self.call = {"topic": topic, "payload": payload, "qos": qos}
        return self.result


class PublisherTests(unittest.TestCase):
    def test_publish_uses_qos_one_and_waits_for_acknowledgment(self):
        result = FakePublishInfo()
        client = FakeMqttClient(result)

        publish_to_central(client, {"aggregate_id": "a-1"}, publish_timeout=7)

        self.assertEqual(client.call["qos"], 1)
        self.assertEqual(result.timeout, 7)

    def test_publish_timeout_keeps_message_available_for_retry(self):
        client = FakeMqttClient(FakePublishInfo(published=False))

        with self.assertRaises(TimeoutError):
            publish_to_central(client, {"aggregate_id": "a-1"}, publish_timeout=1)


if __name__ == "__main__":
    unittest.main()
