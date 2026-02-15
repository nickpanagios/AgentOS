#!/bin/bash
# Task Assignment System
# Usage: assign_task.sh <from> <to> <priority> <task_name> "<description>" "<deadline>"

FROM=$1
TO=$2
PRIORITY=${3:-MEDIUM}
TASK_NAME=$4
DESCRIPTION=$5
DEADLINE=${6:-"none"}
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
TASK_ID="TASK-$(date +%s%N | sha256sum | head -c 8)"

sudo mkdir -p /home/executive-workspace/tasks/{pending,active,completed}

TASK_FILE="/home/executive-workspace/tasks/pending/${TASK_ID}.json"
cat > "$TASK_FILE" << JSONEOF
{
  "id": "${TASK_ID}",
  "from": "${FROM}",
  "to": "${TO}",
  "priority": "${PRIORITY}",
  "name": "${TASK_NAME}",
  "description": "${DESCRIPTION}",
  "deadline": "${DEADLINE}",
  "status": "pending",
  "created": "${TIMESTAMP}",
  "updated": "${TIMESTAMP}"
}
JSONEOF

# Also send as a message
/home/executive-workspace/send_message.sh "$FROM" "$TO" "$PRIORITY" "Task: $TASK_NAME" "New task assigned: $DESCRIPTION [Deadline: $DEADLINE]"

echo "${TIMESTAMP} | ${TASK_ID} | ${FROM} -> ${TO} | ${PRIORITY} | ${TASK_NAME}" >> /home/executive-workspace/logs/task_log.txt
echo "Task assigned: ${TASK_ID} to ${TO} [${PRIORITY}]"
