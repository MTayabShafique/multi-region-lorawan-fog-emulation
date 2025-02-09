#!/bin/sh
set -e

POSTGRESQL_HOST=${POSTGRESQL_HOST:-localhost}
REDIS_HOST=${REDIS_HOST:-localhost}
MQTT_BROKER_HOST=${MQTT_BROKER_HOST:-localhost}

echo "POSTGRESQL_HOST is set to: $POSTGRESQL_HOST"
echo "REDIS_HOST is set to: $REDIS_HOST"
echo "MQTT_BROKER_HOST is set to: $MQTT_BROKER_HOST"

# Wait for PostgreSQL
echo "Waiting for PostgreSQL at $POSTGRESQL_HOST..."
until nc -z -v -w5 "$POSTGRESQL_HOST" 5432; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 3
done
>&2 echo "PostgreSQL is up."

# Wait for Redis
echo "Waiting for Redis at $REDIS_HOST..."
until nc -z -v -w5 "$REDIS_HOST" 6379; do
  >&2 echo "Redis is unavailable - sleeping"
  sleep 3
done
>&2 echo "Redis is up."

# Wait for Mosquitto
echo "Waiting for Mosquitto at $MQTT_BROKER_HOST..."
until nc -z -v -w5 "$MQTT_BROKER_HOST" 1883; do
  >&2 echo "Mosquitto is unavailable - sleeping"
  sleep 3
done
>&2 echo "Mosquitto is up."

echo "All services are up - starting ChirpStack"
exec chirpstack -c /etc/chirpstack/chirpstack.toml
