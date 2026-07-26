import os
import ssl


def configure_mqtt_tls(client):
    if os.getenv("MQTT_TLS_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return

    client.tls_set(
        ca_certs=os.environ["MQTT_TLS_CA"],
        certfile=os.environ["MQTT_TLS_CERT"],
        keyfile=os.environ["MQTT_TLS_KEY"],
        cert_reqs=ssl.CERT_REQUIRED,
        tls_version=ssl.PROTOCOL_TLS_CLIENT,
    )
    client.tls_insecure_set(False)
