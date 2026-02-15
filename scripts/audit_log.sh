#!/bin/bash
# Unified Audit Logger
# Usage: audit_log.sh <category> <agent> <action> "<details>"
# Categories: access, command, change, security

CATEGORY=$1
AGENT=$2
ACTION=$3
DETAILS=$4
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
LOG_ID=$(date +%s%N | sha256sum | head -c 16)
DATE=$(date -u +"%Y-%m-%d")

if [ -z "$CATEGORY" ] || [ -z "$AGENT" ] || [ -z "$ACTION" ]; then
    echo "Usage: audit_log.sh <category> <agent> <action> <details>"
    echo "Categories: access, command, change, security"
    exit 1
fi

LOG_DIR="/home/executive-workspace/audit/${CATEGORY}"
LOG_FILE="${LOG_DIR}/${DATE}.log"

# Structured log entry
echo "${TIMESTAMP}|${LOG_ID}|${AGENT}|${ACTION}|${DETAILS}" >> "$LOG_FILE"

# Also write JSON for machine parsing
JSON_DIR="${LOG_DIR}/json"
mkdir -p "$JSON_DIR"
cat >> "${JSON_DIR}/${DATE}.jsonl" << JSONEOF
{"id":"${LOG_ID}","ts":"${TIMESTAMP}","agent":"${AGENT}","category":"${CATEGORY}","action":"${ACTION}","details":"${DETAILS}"}
JSONEOF
