#!/bin/sh
set -e

# Force the working directory to /etc/chirpstack so that relative includes work.
cd /etc/chirpstack

echo "DEBUG: Current working directory: $(pwd)"
echo "DEBUG: Listing /etc/chirpstack contents:"
ls -la

# Use provided environment variables or default to localhost.
POSTGRESQL_HOST=${POSTGRESQL_HOST:-localhost}
REDIS_HOST=${REDIS_HOST:-localhost}
MQTT_BROKER_HOST=${MQTT_BROKER_HOST:-localhost}

echo "POSTGRESQL_HOST is set to: $POSTGRESQL_HOST"
echo "REDIS_HOST is set to: $REDIS_HOST"
echo "MQTT_BROKER_HOST is set to: $MQTT_BROKER_HOST"

# Wait for PostgreSQL to be ready.
echo "Waiting for PostgreSQL at ${POSTGRESQL_HOST}:5432..."
while ! nc -z "$POSTGRESQL_HOST" 5432; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 3
done
echo "PostgreSQL is up."

# Wait for Redis to be ready.
echo "Waiting for Redis at ${REDIS_HOST}:6379..."
while ! nc -z "$REDIS_HOST" 6379; do
  echo "Redis is unavailable - sleeping"
  sleep 3
done
echo "Redis is up."

# Wait for Mosquitto to be ready.
echo "Waiting for Mosquitto at ${MQTT_BROKER_HOST}:1883..."
while ! nc -z "$MQTT_BROKER_HOST" 1883; do
  echo "Mosquitto is unavailable - sleeping"
  sleep 3
done
echo "Mosquitto is up."

echo "All services are up - starting ChirpStack"
# Pass the configuration directory rather than the file.
exec chirpstack -c /etc/chirpstack
