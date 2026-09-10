#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
credentials_dir="$project_dir/.infisical"
secrets_dir="$project_dir/.secrets"
client_id_file="$credentials_dir/client-id"
client_secret_file="$credentials_dir/client-secret"
config_file="$credentials_dir/config.env"

if [ -f "$config_file" ]; then
    # This ignored file contains only deployment selection, not secret values.
    . "$config_file"
fi

: "${INFISICAL_PROJECT_ID:?Set INFISICAL_PROJECT_ID to the Infisical project ID}"
INFISICAL_ENVIRONMENT=${INFISICAL_ENVIRONMENT:-prod}
INFISICAL_SECRET_PATH=${INFISICAL_SECRET_PATH:-/}
INFISICAL_API_URL=${INFISICAL_API_URL:-https://app.infisical.com}

command -v infisical >/dev/null 2>&1 || {
    echo "Infisical CLI is required: https://infisical.com/docs/cli/overview" >&2
    exit 1
}
command -v python3 >/dev/null 2>&1 || {
    echo "python3 is required to validate the exported JSON" >&2
    exit 1
}

for credential_file in "$client_id_file" "$client_secret_file"; do
    if [ ! -s "$credential_file" ]; then
        echo "Missing Infisical machine credential: $credential_file" >&2
        exit 1
    fi
done

client_id=$(tr -d '\r\n' < "$client_id_file")
client_secret=$(tr -d '\r\n' < "$client_secret_file")
export INFISICAL_API_URL
export INFISICAL_UNIVERSAL_AUTH_CLIENT_ID="$client_id"
export INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET="$client_secret"
export INFISICAL_DISABLE_UPDATE_CHECK=true

access_token=$(infisical login \
    --method=universal-auth \
    --silent \
    --plain)

export_file=$(mktemp)
trap 'rm -f "$export_file"' EXIT HUP INT TERM

INFISICAL_TOKEN="$access_token" infisical export \
    --projectId="$INFISICAL_PROJECT_ID" \
    --env="$INFISICAL_ENVIRONMENT" \
    --path="$INFISICAL_SECRET_PATH" \
    --format=json \
    --output-file="$export_file" >/dev/null

umask 077
mkdir -p "$secrets_dir"
chmod 700 "$secrets_dir"

python3 - "$export_file" "$secrets_dir" <<'PY'
import json
import os
from pathlib import Path
import sys

export_file = Path(sys.argv[1])
secrets_dir = Path(sys.argv[2])

required = {
    "DJANGO_SECRET_KEY": "django_secret_key",
    "DB_PASSWORD": "db_password",
    "RABBITMQ_PASSWORD": "rabbitmq_password",
}

payload = json.loads(export_file.read_text(encoding="utf-8"))

if isinstance(payload, list):
    secrets = {}

    for item in payload:
        if not isinstance(item, dict):
            raise SystemExit(
                "Infisical JSON export contains an invalid secret entry"
            )

        key = item.get("key")
        value = item.get("value")

        if key:
            secrets[key] = value

elif isinstance(payload, dict):
    secrets = payload

else:
    raise SystemExit(
        "Infisical JSON export did not contain a supported secret structure"
    )

missing = sorted(
    key for key in required
    if not secrets.get(key)
)

if missing:
    raise SystemExit(
        "Missing required Infisical secrets: "
        + ", ".join(missing)
    )

for key, filename in required.items():
    destination = secrets_dir / filename
    temporary = secrets_dir / f".{filename}.tmp"

    temporary.write_text(
        str(secrets[key]).strip() + "\n",
        encoding="utf-8",
    )

    os.chmod(temporary, 0o644)
    os.replace(temporary, destination)
PY

unset access_token INFISICAL_UNIVERSAL_AUTH_CLIENT_SECRET client_secret
echo "Synchronized Infisical environment '$INFISICAL_ENVIRONMENT' into Docker Secrets."
