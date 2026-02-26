#!/usr/bin/env bash
# Memory monitoring script for untitledMigrationService
# Usage: ./monitor_memory.sh <pid> [interval_seconds]

PID=${1:-2249791}
INTERVAL=${2:-5}

if [ ! -d "/proc/$PID" ]; then
    echo "Error: Process $PID not found"
    exit 1
fi

echo "Monitoring memory for PID $PID (untitledMigrationService)"
echo "Update interval: ${INTERVAL}s"
echo "Press Ctrl+C to stop"
echo ""
echo "Timestamp                | RSS (bytes)  | RSS (MB)  | VSZ (bytes)  | VSZ (MB)  | Threads | Status"
echo "-------------------------|--------------|-----------|--------------|-----------|---------|-------"

while true; do
    if [ ! -d "/proc/$PID" ]; then
        echo "Process $PID has terminated"
        exit 0
    fi
    
    # Read from /proc/[pid]/status for accurate memory info
    RSS_KB=$(grep "^VmRSS:" /proc/$PID/status | awk '{print $2}')
    VSZ_KB=$(grep "^VmSize:" /proc/$PID/status | awk '{print $2}')
    THREADS=$(grep "^Threads:" /proc/$PID/status | awk '{print $2}')
    
    # Convert to bytes
    RSS_BYTES=$((RSS_KB * 1024))
    VSZ_BYTES=$((VSZ_KB * 1024))
    
    # Convert to MB for readability
    RSS_MB=$(awk "BEGIN {printf \"%.2f\", $RSS_KB/1024}")
    VSZ_MB=$(awk "BEGIN {printf \"%.2f\", $VSZ_KB/1024}")
    
    # Get timestamp
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Get process state
    STATE=$(cat /proc/$PID/status | grep "^State:" | awk '{print $2}')
    
    # Print formatted output
    printf "%s | %12d | %9s | %12d | %9s | %7d | %s\n" \
        "$TIMESTAMP" "$RSS_BYTES" "$RSS_MB" "$VSZ_BYTES" "$VSZ_MB" "$THREADS" "$STATE"
    
    sleep "$INTERVAL"
done
