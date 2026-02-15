#!/bin/bash
# Agent Status Reporter
# Usage: report_status.sh <agent> <status> "<details>"

AGENT=$1
STATUS=${2:-"online"}
DETAILS=$3
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ -z "$AGENT" ]; then
    echo "Usage: report_status.sh <agent> <status> <details>"
    echo "Status: online | busy | idle | offline | error"
    exit 1
fi

STATUS_FILE="/home/executive-workspace/status/${AGENT}.json"
cat > "$STATUS_FILE" << JSONEOF
{
  "agent": "${AGENT}",
  "status": "${STATUS}",
  "details": "${DETAILS}",
  "timestamp": "${TIMESTAMP}",
  "uptime": "$(uptime -p)",
  "load": "$(cat /proc/loadavg | awk '{print $1, $2, $3}')"
}
JSONEOF

echo "${TIMESTAMP} | ${AGENT} | ${STATUS} | ${DETAILS}" >> /home/executive-workspace/logs/status_log.txt
echo "Status updated: ${AGENT} -> ${STATUS}"
