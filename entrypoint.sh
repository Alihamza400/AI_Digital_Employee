#!/bin/sh
set -e

VAULT="${VAULT_PATH:-/app/AI_Employee_Vault}"

# Initialize vault with template files on first run
if [ ! -f "$VAULT/Company_Handbook.md" ]; then
    echo "Initializing vault at $VAULT..."
    mkdir -p "$VAULT"
    if [ -d /app/default-vault ]; then
        cp -r /app/default-vault/* "$VAULT/" 2>/dev/null || true
    fi
fi

exec "$@"
