#!/bin/bash
# Inter-Agent Message Router
# Usage: send_message.sh <from> <to> <priority> <subject> "<message>"

FROM=$1
TO=$2
PRIORITY=${3:-MEDIUM}
SUBJECT=$4
MESSAGE=$5
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
MSG_ID=$(date +%s%N | sha256sum | head -c 12)

if [ -z "$FROM" ] || [ -z "$TO" ] || [ -z "$MESSAGE" ]; then
    echo "Usage: send_message.sh <from> <to> <priority> <subject> <message>"
    echo "Priority: CRITICAL | HIGH | MEDIUM | LOW"
    exit 1
fi

# Create message JSON
MSG_FILE="/home/executive-workspace/messages/inbox/${TO}/${MSG_ID}.json"
cat > "$MSG_FILE" << JSONEOF
{
  "id": "${MSG_ID}",
  "from": "${FROM}",
  "to": "${TO}",
  "priority": "${PRIORITY}",
  "subject": "${SUBJECT}",
  "message": "${MESSAGE}",
  "timestamp": "${TIMESTAMP}",
  "status": "unread",
  "type": "direct"
}
JSONEOF

# Copy to sender's outbox
cp "$MSG_FILE" "/home/executive-workspace/messages/outbox/${FROM}/${MSG_ID}.json"

# Log the message
echo "${TIMESTAMP} | ${MSG_ID} | ${FROM} -> ${TO} | ${PRIORITY} | ${SUBJECT}" >> /home/executive-workspace/logs/message_log.txt

echo "Message sent: ${MSG_ID} from ${FROM} to ${TO} [${PRIORITY}]"
