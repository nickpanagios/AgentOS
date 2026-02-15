#!/bin/bash
# Audit Report Generator
# Usage: audit_report.sh [date] [category] [agent]

DATE=${1:-$(date -u +"%Y-%m-%d")}
CATEGORY=$2
AGENT=$3

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    AUDIT REPORT                             ║"
echo "║  Date: $DATE                                        ║"
echo "╠══════════════════════════════════════════════════════════════╣"

CATEGORIES="access commands changes security"
if [ -n "$CATEGORY" ]; then
    CATEGORIES="$CATEGORY"
fi

TOTAL=0
for CAT in $CATEGORIES; do
    LOG_FILE="/home/executive-workspace/audit/${CAT}/${DATE}.log"
    if [ -f "$LOG_FILE" ]; then
        if [ -n "$AGENT" ]; then
            COUNT=$(grep "|${AGENT}|" "$LOG_FILE" | wc -l)
        else
            COUNT=$(wc -l < "$LOG_FILE")
        fi
        TOTAL=$((TOTAL + COUNT))
        printf "║  %-12s: %d entries" "$CAT" "$COUNT"
        echo ""
        
        # Show last 5 entries
        if [ -n "$AGENT" ]; then
            grep "|${AGENT}|" "$LOG_FILE" | tail -5 | while IFS='|' read TS ID AG ACT DET; do
                printf "║    %s | %-10s | %-10s | %s\n" "$TS" "$AG" "$ACT" "$DET"
            done
        else
            tail -5 "$LOG_FILE" | while IFS='|' read TS ID AG ACT DET; do
                printf "║    %s | %-10s | %-10s | %s\n" "$TS" "$AG" "$ACT" "$DET"
            done
        fi
    else
        printf "║  %-12s: no entries\n" "$CAT"
    fi
done

echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Total entries: $TOTAL"
echo "╚══════════════════════════════════════════════════════════════╝"
