#!/bin/bash
# File Integrity Monitor — baseline & verify critical files
# Usage: integrity_check.sh [baseline|verify]

ACTION=${1:-verify}
BASELINE_FILE="/home/executive-workspace/audit/security/integrity_baseline.sha256"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Critical files to monitor
CRITICAL_FILES=(
    "/home/executive-workspace/send_message.sh"
    "/home/executive-workspace/broadcast.sh"
    "/home/executive-workspace/read_messages.sh"
    "/home/executive-workspace/report_status.sh"
    "/home/executive-workspace/assign_task.sh"
    "/home/executive-workspace/notify.sh"
    "/home/executive-workspace/dashboard.sh"
    "/home/executive-workspace/audit_log.sh"
    "/home/executive-workspace/config/routing.json"
    "/home/ubuntu/shared-repo/config/agent-specializations.json"
)

if [ "$ACTION" == "baseline" ]; then
    echo "Creating integrity baseline at $TIMESTAMP..."
    echo "# Integrity Baseline — $TIMESTAMP" > "$BASELINE_FILE"
    for FILE in "${CRITICAL_FILES[@]}"; do
        if [ -f "$FILE" ]; then
            HASH=$(sha256sum "$FILE")
            echo "$HASH" >> "$BASELINE_FILE"
            echo "  ✅ $FILE"
        else
            echo "  ⚠️  $FILE (not found)"
        fi
    done
    echo "Baseline saved to $BASELINE_FILE"
    /home/executive-workspace/audit_log.sh security system baseline_created "Integrity baseline created with ${#CRITICAL_FILES[@]} files"

elif [ "$ACTION" == "verify" ]; then
    if [ ! -f "$BASELINE_FILE" ]; then
        echo "❌ No baseline found. Run: integrity_check.sh baseline"
        exit 1
    fi
    
    echo "Verifying file integrity at $TIMESTAMP..."
    VIOLATIONS=0
    for FILE in "${CRITICAL_FILES[@]}"; do
        if [ -f "$FILE" ]; then
            CURRENT_HASH=$(sha256sum "$FILE" | awk '{print $1}')
            BASELINE_HASH=$(grep "$FILE" "$BASELINE_FILE" | awk '{print $1}')
            if [ "$CURRENT_HASH" == "$BASELINE_HASH" ]; then
                echo "  ✅ $FILE — intact"
            else
                echo "  🚨 $FILE — MODIFIED"
                VIOLATIONS=$((VIOLATIONS + 1))
                /home/executive-workspace/audit_log.sh security system integrity_violation "File modified: $FILE"
            fi
        else
            echo "  🚨 $FILE — MISSING"
            VIOLATIONS=$((VIOLATIONS + 1))
            /home/executive-workspace/audit_log.sh security system integrity_violation "File missing: $FILE"
        fi
    done
    
    if [ $VIOLATIONS -eq 0 ]; then
        echo ""
        echo "✅ All ${#CRITICAL_FILES[@]} files passed integrity check"
    else
        echo ""
        echo "🚨 $VIOLATIONS INTEGRITY VIOLATION(S) DETECTED"
    fi
fi
