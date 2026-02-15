#!/bin/bash
# Broadcast Message to All Executives
# Usage: broadcast.sh <from> <priority> <subject> "<message>"

FROM=$1
PRIORITY=${2:-MEDIUM}
SUBJECT=$3
MESSAGE=$4
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BROADCAST_ID=$(date +%s%N | sha256sum | head -c 12)

EXECUTIVES="jarvis tesla warren steve tony"

for EXEC in $EXECUTIVES; do
    if [ "$EXEC" != "$FROM" ]; then
        MSG_FILE="/home/executive-workspace/messages/inbox/${EXEC}/${BROADCAST_ID}_${FROM}.json"
        cat > "$MSG_FILE" << JSONEOF
{
  "id": "${BROADCAST_ID}",
  "from": "${FROM}",
  "to": "${EXEC}",
  "priority": "${PRIORITY}",
  "subject": "${SUBJECT}",
  "message": "${MESSAGE}",
  "timestamp": "${TIMESTAMP}",
  "status": "unread",
  "type": "broadcast"
}
JSONEOF
    fi
done

# Archive broadcast
cp_file="/home/executive-workspace/messages/broadcast/${BROADCAST_ID}.json"
cat > "$cp_file" << JSONEOF
{
  "id": "${BROADCAST_ID}",
  "from": "${FROM}",
  "priority": "${PRIORITY}",
  "subject": "${SUBJECT}",
  "message": "${MESSAGE}",
  "timestamp": "${TIMESTAMP}",
  "recipients": "all-executives",
  "type": "broadcast"
}
JSONEOF

echo "${TIMESTAMP} | BROADCAST | ${BROADCAST_ID} | ${FROM} -> ALL | ${PRIORITY} | ${SUBJECT}" >> /home/executive-workspace/logs/message_log.txt
echo "Broadcast sent: ${BROADCAST_ID} from ${FROM} to all executives [${PRIORITY}]"
