#!/bin/bash
# Sub-Agent Message System
# Usage: sub_message.sh <from_agent> <to_agent_or_exec> <priority> <subject> "<message>"

FROM=$1
TO=$2
PRIORITY=${3:-MEDIUM}
SUBJECT=$4
MESSAGE=$5
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
MSG_ID=$(date +%s%N | sha256sum | head -c 12)

if [ -z "$FROM" ] || [ -z "$TO" ] || [ -z "$MESSAGE" ]; then
    echo "Usage: sub_message.sh <from> <to> <priority> <subject> <message>"
    exit 1
fi

# Determine teams
declare -A TEAM_OF
for a in backend frontend ai-mlops devops-engineer security-engineer data-engineer; do TEAM_OF[$a]="tesla"; done
for a in financial-analyst accounting-specialist resource-manager administrative-coordinator; do TEAM_OF[$a]="warren"; done
for a in brand-strategist content-creator social-media-manager seo-specialist analytics-expert; do TEAM_OF[$a]="steve"; done
for a in contract-specialist compliance-analyst intellectual-property litigation-support corporate-governance; do TEAM_OF[$a]="tony"; done
for a in jarvis tesla warren steve tony; do TEAM_OF[$a]="executive"; done

FROM_TEAM=${TEAM_OF[$FROM]}
TO_TEAM=${TEAM_OF[$TO]}

# Create message JSON
MSG_JSON="{\"id\":\"${MSG_ID}\",\"from\":\"${FROM}\",\"to\":\"${TO}\",\"priority\":\"${PRIORITY}\",\"subject\":\"${SUBJECT}\",\"message\":\"${MESSAGE}\",\"timestamp\":\"${TIMESTAMP}\",\"status\":\"unread\",\"type\":\"sub-agent\"}"

# Route message
if [ "$TO_TEAM" = "executive" ]; then
    # Sub-agent to executive — use main message system
    echo "$MSG_JSON" > "/home/executive-workspace/messages/inbox/${TO}/${MSG_ID}.json"
    echo "Message sent to executive $TO: $MSG_ID [$PRIORITY]"
elif [ "$FROM_TEAM" = "$TO_TEAM" ]; then
    # Same team — route within team workspace
    TEAM_DIR="/home/executive-workspace/teams/$FROM_TEAM"
    echo "$MSG_JSON" > "$TEAM_DIR/messages/${TO}/inbox/${MSG_ID}.json"
    echo "$MSG_JSON" > "$TEAM_DIR/messages/${FROM}/outbox/${MSG_ID}.json"
    echo "Intra-team message: $FROM -> $TO [$PRIORITY] ($MSG_ID)"
else
    # Cross-team — route through both team workspaces
    FROM_DIR="/home/executive-workspace/teams/$FROM_TEAM"
    TO_DIR="/home/executive-workspace/teams/$TO_TEAM"
    echo "$MSG_JSON" > "$TO_DIR/messages/${TO}/inbox/${MSG_ID}.json" 2>/dev/null
    echo "$MSG_JSON" > "$FROM_DIR/messages/${FROM}/outbox/${MSG_ID}.json" 2>/dev/null
    echo "Cross-team message: $FROM ($FROM_TEAM) -> $TO ($TO_TEAM) [$PRIORITY] ($MSG_ID)"
fi

# Log
echo "${TIMESTAMP}|${MSG_ID}|${FROM}|${TO}|${PRIORITY}|${SUBJECT}" >> /home/executive-workspace/logs/sub_message_log.txt 2>/dev/null
