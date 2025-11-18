#!/bin/bash
set -e

setup_synapse_homeserver() {
    PORT="$1"
    ID="$2"

    SERVER_NAME="my.matrix.host${ID}"
    VOLNAME="synapse${ID}-data"
    CONTAINER_NAME="synapse${ID}"

    #remove volume if exists (self contained testing environment)
    docker rm -f "$CONTAINER_NAME"
    docker volume rm -f "$VOLNAME"

    docker run --rm \
        --mount type=volume,src="$VOLNAME",dst=/data \
        -e SYNAPSE_SERVER_NAME="$SERVER_NAME" \
        -e SYNAPSE_REPORT_STATS=yes \
        matrixdotorg/synapse:v1.138.0 generate

    docker run --rm \
    -v "$(docker volume inspect --format '{{.Mountpoint}}' "$VOLNAME")":/data \
    alpine sh -c "cat >> /data/homeserver.yaml <<'EOF'

enable_registration: true
enable_registration_without_verification: true

rc_login:
  address:
    per_second: 1000
    burst_count: 1000
  account:
    per_second: 1000
    burst_count: 1000
  failed_attempts:
    per_second: 1000
    burst_count: 1000

rc_message:
  per_second: 1000
  burst_count: 1000
rc_registration:
  per_second: 1000
  burst_count: 1000
EOF"

    docker run -d --name "$CONTAINER_NAME" \
        --mount type=volume,src="$VOLNAME",dst=/data \
        -p "${PORT}:8008" \
        --restart unless-stopped \
        matrixdotorg/synapse:latest

    echo "Synapse $CONTAINER_NAME running at http://localhost:${PORT}"
}

setup_synapse_homeserver 8008 1
# setup_synapse_homeserver 8009 2

