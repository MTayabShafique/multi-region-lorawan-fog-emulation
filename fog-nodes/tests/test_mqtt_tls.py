import os
import ssl
import unittest
from unittest.mock import MagicMock, patch

from mqtt_client import setup_mqtt_client


class MqttTlsTests(unittest.TestCase):
    @patch("mqtt_client.mqtt.Client")
    def test_client_requires_verified_mutual_tls(self, client_factory):
        client = MagicMock()
        client_factory.return_value = client
        environment = {
            "MQTT_TLS_ENABLED": "true",
            "MQTT_TLS_CA": "/run/mqtt-certs/ca.crt",
            "MQTT_TLS_CERT": "/run/mqtt-certs/client.crt",
            "MQTT_TLS_KEY": "/run/mqtt-certs/client.key",
        }

        with patch.dict(os.environ, environment, clear=True):
            setup_mqtt_client("worker-1", "eu868", "region/eu868/#", MagicMock())

        client.tls_set.assert_called_once_with(
            ca_certs="/run/mqtt-certs/ca.crt",
            certfile="/run/mqtt-certs/client.crt",
            keyfile="/run/mqtt-certs/client.key",
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.tls_insecure_set.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
