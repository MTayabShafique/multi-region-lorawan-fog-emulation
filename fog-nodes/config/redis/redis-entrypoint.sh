#!/bin/sh
set -eu

password="${REDIS_PASSWORD:-}"
if [ -z "$password" ]; then
    password="$(cat "${REDIS_PASSWORD_FILE:-/run/secrets/redis_password}")"
fi
config_file="/tmp/redis.conf"

cat > "$config_file" <<EOF
bind 0.0.0.0
protected-mode yes
port 6379
dir /data
requirepass ${password}
masterauth ${password}
appendonly yes
appendfsync everysec
save 60 100
replica-announce-ip ${REDIS_ANNOUNCE_HOST}
replica-announce-port 6379
min-replicas-to-write 1
min-replicas-max-lag 10
EOF

if [ "${REDIS_INITIAL_ROLE:-replica}" = "replica" ]; then
    printf 'replicaof %s 6379\n' "${REDIS_INITIAL_MASTER_HOST:-fog-redis1}" >> "$config_file"
fi

exec redis-server "$config_file"
