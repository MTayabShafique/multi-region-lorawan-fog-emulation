#!/bin/sh
set -e

echo "Waiting for HAProxy to be ready on haproxy:1883..."
# Use netcat to check haproxy:1883. Adjust the sleep time if needed.
while ! nc -z haproxy 1883; do
  echo "HAProxy not ready yet - sleeping..."
  sleep 2
done

echo "HAProxy is up - starting ChirpStack."
exec "$@"
