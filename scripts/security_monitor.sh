#!/bin/bash
# Security Monitor — run periodically to check system health
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║              SECURITY MONITOR — $TIMESTAMP            ║"
echo "╠══════════════════════════════════════════════════════════════╣"

ALERTS=0

# 1. Check for unauthorized permission changes on exec homes
echo "║ [1] Home Directory Permissions"
for user in jarvis tesla warren steve tony; do
    PERMS=$(stat -c "%a" /home/$user 2>/dev/null)
    if [ "$PERMS" != "750" ]; then
        echo "║   🚨 /home/$user has permissions $PERMS (expected 750)"
        ALERTS=$((ALERTS + 1))
    else
        echo "║   ✅ /home/$user — 750"
    fi
done

# 2. Check for world-readable files in sensitive dirs
echo "║"
echo "║ [2] World-Readable Files in Sensitive Directories"
WORLD_READ=$(find /home/executive-workspace -perm -o+r -type f 2>/dev/null | wc -l)
if [ "$WORLD_READ" -gt 0 ]; then
    echo "║   ⚠️  $WORLD_READ world-readable files found"
    ALERTS=$((ALERTS + 1))
else
    echo "║   ✅ No world-readable files in executive workspace"
fi

# 3. Check for failed login attempts
echo "║"
echo "║ [3] Failed Login Attempts (last 24h)"
FAILED=$(sudo grep "Failed password" /var/log/auth.log 2>/dev/null | grep "$(date +%b\ %d)" | wc -l)
echo "║   ℹ️  $FAILED failed login attempts today"
if [ "$FAILED" -gt 10 ]; then
    echo "║   🚨 HIGH number of failed logins — possible brute force"
    ALERTS=$((ALERTS + 1))
fi

# 4. Check running processes for anomalies
echo "║"
echo "║ [4] Process Check"
AGENT_PROCS=$(ps aux | grep -E "^(jarvis|tesla|warren|steve|tony)" | grep -v grep | wc -l)
echo "║   ℹ️  $AGENT_PROCS processes running under agent accounts"

# 5. Check disk usage
echo "║"
echo "║ [5] Disk Usage"
DISK_PCT=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
echo "║   ℹ️  Disk usage: ${DISK_PCT}%"
if [ "$DISK_PCT" -gt 85 ]; then
    echo "║   🚨 Disk usage above 85% threshold"
    ALERTS=$((ALERTS + 1))
fi

# 6. Check memory
echo "║"
echo "║ [6] Memory Usage"
MEM_PCT=$(free | awk '/Mem:/ {printf "%.0f", $3/$2*100}')
echo "║   ℹ️  Memory usage: ${MEM_PCT}%"
if [ "$MEM_PCT" -gt 90 ]; then
    echo "║   🚨 Memory usage above 90% threshold"
    ALERTS=$((ALERTS + 1))
fi

# 7. File integrity check
echo "║"
echo "║ [7] File Integrity"
if [ -f /home/executive-workspace/audit/security/integrity_baseline.sha256 ]; then
    VIOLATIONS=0
    while IFS= read -r line; do
        [[ "$line" == "#"* ]] && continue
        FILE=$(echo "$line" | awk '{print $2}')
        EXPECTED=$(echo "$line" | awk '{print $1}')
        [ -z "$FILE" ] && continue
        if [ -f "$FILE" ]; then
            ACTUAL=$(sha256sum "$FILE" | awk '{print $1}')
            if [ "$ACTUAL" != "$EXPECTED" ]; then
                VIOLATIONS=$((VIOLATIONS + 1))
            fi
        else
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    done < /home/executive-workspace/audit/security/integrity_baseline.sha256
    
    if [ "$VIOLATIONS" -eq 0 ]; then
        echo "║   ✅ All critical files intact"
    else
        echo "║   🚨 $VIOLATIONS file integrity violations!"
        ALERTS=$((ALERTS + 1))
    fi
else
    echo "║   ⚠️  No integrity baseline — run integrity_check.sh baseline"
fi

# 8. Check SSH keys
echo "║"
echo "║ [8] SSH Key Audit"
for user in jarvis tesla warren steve tony; do
    KEY_COUNT=$(sudo ls /home/$user/.ssh/authorized_keys 2>/dev/null | wc -l)
    if [ -f "/home/$user/.ssh/authorized_keys" ]; then
        KEYS=$(sudo wc -l < /home/$user/.ssh/authorized_keys 2>/dev/null)
        echo "║   ℹ️  $user: $KEYS authorized SSH key(s)"
    fi
done

echo "║"
echo "╠══════════════════════════════════════════════════════════════╣"
if [ "$ALERTS" -eq 0 ]; then
    echo "║  ✅ SECURITY STATUS: ALL CLEAR — 0 alerts                  ║"
else
    echo "║  🚨 SECURITY STATUS: $ALERTS ALERT(S) REQUIRE ATTENTION       ║"
fi
echo "╚══════════════════════════════════════════════════════════════╝"

# Log the scan
/home/executive-workspace/audit_log.sh security system security_scan "Completed: $ALERTS alerts"
