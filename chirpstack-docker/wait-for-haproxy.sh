#!/bin/sh
set -e

echo "Waiting for HAProxy to be ready on chirpstack-haproxy:8883..."
# A TCP check confirms that the TLS passthrough listener is accepting connections.
while ! nc -z chirpstack-haproxy 8883; do
  echo "HAProxy not ready yet - sleeping..."
  sleep 2
done

echo "HAProxy is up - starting ChirpStack."
exec "$@"
