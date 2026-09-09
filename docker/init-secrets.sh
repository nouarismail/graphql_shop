#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
secrets_dir="$project_dir/.secrets"

umask 077
mkdir -p "$secrets_dir"

create_secret() {
    destination=$1
    byte_count=$2
    if [ -e "$destination" ]; then
        echo "Keeping existing $(basename "$destination")"
        return
    fi
    openssl rand -hex "$byte_count" > "$destination"
    echo "Created $(basename "$destination")"
}

create_secret "$secrets_dir/django_secret_key" 32
create_secret "$secrets_dir/db_password" 24
create_secret "$secrets_dir/rabbitmq_password" 24

chmod 700 "$secrets_dir"
# Local Compose file-backed secrets retain source permissions. The directory is
# private on the host; readable files allow the non-root app user to read mounts.
chmod 644 "$secrets_dir"/*

echo "Secrets are ready in $secrets_dir (private directory, read-only mounts)."
