#!/usr/bin/env bash
# Usage: ./scripts/push-skill-env.sh [sandbox-container-name]
#
# Copies sentiment-agent/.env into the running sandbox and restarts the skill.
# Run this whenever you add or change env vars — no rebuild needed.

set -euo pipefail

SKILL_NAME="market-sentiment"
ENV_FILE="$(dirname "$0")/../sentiment-agent/.env"
CONTAINER="${1:-}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found. Copy .env.example and fill in values first."
  exit 1
fi

# Find the sandbox container automatically if not supplied
if [[ -z "$CONTAINER" ]]; then
  CONTAINER=$(docker ps --format "{{.Names}}" | grep -v "openshell-cluster" | head -1)
  if [[ -z "$CONTAINER" ]]; then
    echo "ERROR: No sandbox container found. Is the sandbox running?"
    docker ps --format "{{.Names}}\t{{.Image}}"
    exit 1
  fi
fi

echo "Target container: $CONTAINER"

# Find where the skill was installed inside the sandbox
SKILL_PATH=$(docker exec "$CONTAINER" find / -type f -name "main.py" -path "*${SKILL_NAME}*" 2>/dev/null | head -1)
if [[ -z "$SKILL_PATH" ]]; then
  echo "ERROR: Could not find $SKILL_NAME skill inside $CONTAINER."
  echo "Has the skill been installed? Run: nemoclaw $CONTAINER skill install ./sentiment-agent"
  exit 1
fi

SKILL_DIR=$(dirname "$SKILL_PATH")
echo "Skill directory: $SKILL_DIR"

# Push the .env file
docker cp "$ENV_FILE" "$CONTAINER:$SKILL_DIR/.env"
echo ".env pushed."

# Restart the skill process
PID=$(docker exec "$CONTAINER" pgrep -f "${SKILL_NAME}/main.py" 2>/dev/null || true)
if [[ -n "$PID" ]]; then
  docker exec "$CONTAINER" kill "$PID"
  echo "Killed existing skill process (pid $PID). Cron will restart it on next @reboot, or start manually:"
  echo "  docker exec $CONTAINER bash -c 'nohup python $SKILL_DIR/main.py >> /var/log/market-sentiment.log 2>&1 &'"
else
  echo "Skill not currently running. Start it with:"
  echo "  docker exec $CONTAINER bash -c 'nohup python $SKILL_DIR/main.py >> /var/log/market-sentiment.log 2>&1 &'"
fi
