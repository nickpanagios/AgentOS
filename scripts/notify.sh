#!/bin/bash
# Notification System
# Usage: notify.sh <type> <agent> <priority> "<message>"

TYPE=$1
AGENT=$2
PRIORITY=${3:-MEDIUM}
MESSAGE=$4
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
NOTIFY_ID=$(date +%s%N | sha256sum | head -c 10)

sudo mkdir -p /home/executive-workspace/notifications

NOTIFY_FILE="/home/executive-workspace/notifications/${NOTIFY_ID}.json"
cat > "$NOTIFY_FILE" << JSONEOF
{
  "id": "${NOTIFY_ID}",
  "type": "${TYPE}",
  "agent": "${AGENT}",
  "priority": "${PRIORITY}",
  "message": "${MESSAGE}",
  "timestamp": "${TIMESTAMP}",
  "acknowledged": false
}
JSONEOF

echo "${TIMESTAMP} | ${NOTIFY_ID} | ${TYPE} | ${AGENT} | ${PRIORITY} | ${MESSAGE}" >> /home/executive-workspace/logs/notification_log.txt

case $PRIORITY in
    CRITICAL) echo "🚨 CRITICAL NOTIFICATION for ${AGENT}: ${MESSAGE}";;
    HIGH)     echo "⚠️  HIGH NOTIFICATION for ${AGENT}: ${MESSAGE}";;
    MEDIUM)   echo "ℹ️  NOTIFICATION for ${AGENT}: ${MESSAGE}";;
    LOW)      echo "📝 LOW NOTIFICATION for ${AGENT}: ${MESSAGE}";;
esac
