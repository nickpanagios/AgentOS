#!/bin/bash
# Executive Dashboard - Real-time Agent Status
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              EXECUTIVE AGENT DASHBOARD                      ║"
echo "║              $(date -u +"%Y-%m-%d %H:%M:%S UTC")                    ║"
echo "╠══════════════════════════════════════════════════════════════╣"

EXECUTIVES="jarvis tesla warren steve tony"
for EXEC in $EXECUTIVES; do
    STATUS_FILE="/home/executive-workspace/status/${EXEC}.json"
    if [ -f "$STATUS_FILE" ]; then
        STATUS=$(jq -r '.status' "$STATUS_FILE" 2>/dev/null)
        DETAILS=$(jq -r '.details' "$STATUS_FILE" 2>/dev/null)
        LAST_UPDATE=$(jq -r '.timestamp' "$STATUS_FILE" 2>/dev/null)
        case $STATUS in
            online)  ICON="🟢";;
            busy)    ICON="🟡";;
            idle)    ICON="🔵";;
            offline) ICON="🔴";;
            error)   ICON="⚠️";;
            *)       ICON="⚪";;
        esac
    else
        ICON="⚪"
        STATUS="unknown"
        DETAILS="No status reported"
        LAST_UPDATE="N/A"
    fi
    
    # Get message count
    INBOX="/home/executive-workspace/messages/inbox/${EXEC}"
    MSG_COUNT=$(ls "$INBOX"/*.json 2>/dev/null | wc -l)
    
    printf "║ %s %-10s | Status: %-8s | Msgs: %-3s | %-15s ║\n" "$ICON" "${EXEC^^}" "$STATUS" "$MSG_COUNT" "$DETAILS"
done

echo "╠══════════════════════════════════════════════════════════════╣"
echo "║ System Load: $(cat /proc/loadavg | awk '{print $1, $2, $3}')                                    ║"
echo "║ Memory: $(free -h | awk '/Mem:/ {printf "%s/%s (%.0f%%)", $3, $2, $3/$2*100}')                              ║"
echo "║ Disk: $(df -h / | awk 'NR==2 {printf "%s/%s (%s)", $3, $2, $5}')                                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
