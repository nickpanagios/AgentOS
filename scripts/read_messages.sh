#!/bin/bash
# Read Messages for an Executive
# Usage: read_messages.sh <executive> [priority_filter]

EXEC=$1
PRIORITY_FILTER=$2
INBOX="/home/executive-workspace/messages/inbox/${EXEC}"

if [ -z "$EXEC" ]; then
    echo "Usage: read_messages.sh <executive> [priority_filter]"
    exit 1
fi

if [ ! -d "$INBOX" ]; then
    echo "No inbox found for ${EXEC}"
    exit 1
fi

MSG_COUNT=$(ls "$INBOX"/*.json 2>/dev/null | wc -l)
echo "=== INBOX: ${EXEC} (${MSG_COUNT} messages) ==="
echo ""

for msg in "$INBOX"/*.json; do
    [ -f "$msg" ] || continue
    
    FROM=$(jq -r '.from' "$msg" 2>/dev/null)
    PRIORITY=$(jq -r '.priority' "$msg" 2>/dev/null)
    SUBJECT=$(jq -r '.subject' "$msg" 2>/dev/null)
    STATUS=$(jq -r '.status' "$msg" 2>/dev/null)
    TIMESTAMP=$(jq -r '.timestamp' "$msg" 2>/dev/null)
    
    if [ -n "$PRIORITY_FILTER" ] && [ "$PRIORITY" != "$PRIORITY_FILTER" ]; then
        continue
    fi
    
    echo "[$PRIORITY] From: $FROM | Subject: $SUBJECT"
    echo "  Time: $TIMESTAMP | Status: $STATUS"
    echo "  Message: $(jq -r '.message' "$msg" 2>/dev/null | head -c 100)"
    echo ""
done
