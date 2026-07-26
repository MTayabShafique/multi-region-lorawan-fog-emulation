#!/bin/sh
set -eu

password="${REDIS_PASSWORD:-}"
if [ -z "$password" ]; then
    password="$(cat "${REDIS_PASSWORD_FILE:-/run/secrets/redis_password}")"
fi
config_file="/data/sentinel.conf"

if [ ! -s "$config_file" ]; then
    cat > "$config_file" <<EOF
bind 0.0.0.0
protected-mode yes
port 26379
dir /data
requirepass ${password}
sentinel resolve-hostnames yes
sentinel announce-hostnames yes
sentinel announce-ip ${SENTINEL_ANNOUNCE_HOST}
sentinel announce-port 26379
sentinel monitor ${REDIS_MASTER_NAME:-sensiot-fog} ${REDIS_INITIAL_MASTER_HOST:-fog-redis1} 6379 2
sentinel auth-pass ${REDIS_MASTER_NAME:-sensiot-fog} ${password}
sentinel down-after-milliseconds ${REDIS_MASTER_NAME:-sensiot-fog} ${REDIS_DOWN_AFTER_MS:-5000}
sentinel failover-timeout ${REDIS_MASTER_NAME:-sensiot-fog} ${REDIS_FAILOVER_TIMEOUT_MS:-60000}
sentinel parallel-syncs ${REDIS_MASTER_NAME:-sensiot-fog} ${REDIS_PARALLEL_SYNCS:-1}
sentinel deny-scripts-reconfig yes
EOF
fi

exec redis-server "$config_file" --sentinel
