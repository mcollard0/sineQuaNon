#!/bin/bash
#
# Fast Drive Test for nvme2 using native tools
# Fills with zeros, verifies, recreates filesystem
# WARNING: DESTROYS ALL DATA on the device!
#

set -e;  # Exit on error;

DEVICE="/dev/nvme2n1";
PARTITION="/dev/nvme2n1p1";
MOUNT_POINT="/Media/3";
BLOCK_SIZE="128M";  # 128MB blocks for optimal NVMe performance;
REPORT_FILE="drive_test_report_$(date +%Y%m%d_%H%M%S).txt";

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$REPORT_FILE";
}

log_divider() {
    log "============================================================";
}

# Get drive size in bytes;
get_drive_size() {
    sudo blockdev --getsize64 "$DEVICE";
}

# Convert bytes to human readable;
human_size() {
    numfmt --to=iec-i --suffix=B "$1";
}

log_divider;
log "Drive Test Program - nvme2 (Fast Version)";
log_divider;
log "Device: $DEVICE";
log "Partition: $PARTITION";
log "Mount point: $MOUNT_POINT";
log "";

# Confirmation;
echo "============================================================";
echo "WARNING: THIS WILL DESTROY ALL DATA ON $DEVICE!";
echo "============================================================";
read -p "Type 'DESTROY' to continue: " response;
if [ "$response" != "DESTROY" ]; then
    echo "Aborted.";
    exit 0;
fi

START_TIME=$(date +%s);

# Save current vfs_cache_pressure and set to lower value;
log "Saving current vfs_cache_pressure...";
ORIG_VFS_CACHE_PRESSURE=$(cat /proc/sys/vm/vfs_cache_pressure);
log "Current vfs_cache_pressure: $ORIG_VFS_CACHE_PRESSURE";
log "Setting vfs_cache_pressure to 10 (favor caching)...";
echo 10 | sudo tee /proc/sys/vm/vfs_cache_pressure > /dev/null;
log "New vfs_cache_pressure: $(cat /proc/sys/vm/vfs_cache_pressure)";
log "";

# Cleanup function to restore settings;
cleanup() {
    log "";
    log "Restoring original settings...";
    log "Restoring vfs_cache_pressure to $ORIG_VFS_CACHE_PRESSURE...";
    echo "$ORIG_VFS_CACHE_PRESSURE" | sudo tee /proc/sys/vm/vfs_cache_pressure > /dev/null;
    log "Restored vfs_cache_pressure: $(cat /proc/sys/vm/vfs_cache_pressure)";
}

# Register cleanup on exit;
trap cleanup EXIT;

# Get drive size;
log "Getting drive size...";
DRIVE_SIZE=$(get_drive_size);
DRIVE_SIZE_HUMAN=$(human_size "$DRIVE_SIZE");
log "Drive size: $DRIVE_SIZE bytes ($DRIVE_SIZE_HUMAN)";
log "";

# Get current readahead and set to maximum;
log "Optimizing readahead settings...";
CURRENT_RA=$(sudo blockdev --getra "$DEVICE");
log "Current readahead: $CURRENT_RA sectors";
log "Setting readahead to maximum (256MB = 524288 sectors)...";
sudo blockdev --setra 524288 "$DEVICE";
NEW_RA=$(sudo blockdev --getra "$DEVICE");
log "New readahead: $NEW_RA sectors ($((NEW_RA / 2048)) MB)";
log "";

# Set I/O scheduler to none for best NVMe performance;
DEVICE_NAME=$(basename "$DEVICE");
SCHED_PATH="/sys/block/${DEVICE_NAME}/queue/scheduler";
if [ -f "$SCHED_PATH" ]; then
    log "Optimizing I/O scheduler...";
    ORIG_SCHEDULER=$(cat "$SCHED_PATH" | grep -oP '\[\K[^\]]+');
    log "Current scheduler: $ORIG_SCHEDULER";
    if grep -q "none" "$SCHED_PATH"; then
        echo none | sudo tee "$SCHED_PATH" > /dev/null;
        log "Set scheduler to: none (direct hardware access)";
    else
        log "'none' scheduler not available, keeping $ORIG_SCHEDULER";
    fi
    log "";
fi;

# Drop caches to ensure clean test;
log "Dropping filesystem caches...";
sudo sync;
echo 3 | sudo tee /proc/sys/vm/drop_caches > /dev/null;
log "Caches dropped";
log "";

# Unmount if mounted;
log_divider;
log "Unmounting drive...";
if mountpoint -q "$MOUNT_POINT"; then
    sudo umount "$MOUNT_POINT";
    log "Unmounted $MOUNT_POINT";
else
    log "Not mounted";
fi
log "";

# PHASE 1: Fill with zeros;
log_divider;
log "PHASE 1: Filling drive with zeros";
log_divider;
log "Using dd with bs=$BLOCK_SIZE";
log "This may take several hours...";
log "";

WRITE_START=$(date +%s);
sudo dd if=/dev/zero of="$DEVICE" bs="$BLOCK_SIZE" oflag=direct status=progress 2>&1 | tee -a "$REPORT_FILE";
WRITE_END=$(date +%s);
WRITE_DURATION=$((WRITE_END - WRITE_START));
WRITE_SPEED=$((DRIVE_SIZE / WRITE_DURATION / 1024 / 1024));

log "";
log "Write completed in $WRITE_DURATION seconds ($((WRITE_DURATION / 60)) minutes)";
log "Write speed: ${WRITE_SPEED} MB/s";
log "";

# Sync to ensure all writes are flushed;
log "Syncing...";
sync;
log "";

# PHASE 2: Verify zeros;
log_divider;
log "PHASE 2: Verifying all data is zeros";
log_divider;
log "Using cmp to compare device with /dev/zero";
log "";

READ_START=$(date +%s);

# Use cmp to compare - it will report first difference;
# We need to limit /dev/zero to the drive size;
# Note: cmp doesn't support direct I/O flags, but kernel will optimize large sequential reads;
if sudo cmp -n "$DRIVE_SIZE" "$DEVICE" /dev/zero 2>&1 | tee -a "$REPORT_FILE"; then
    VERIFY_RESULT="SUCCESS";
    log "";
    log "✓ SUCCESS: All $DRIVE_SIZE bytes verified as zeros";
else
    VERIFY_RESULT="FAILURE";
    CMP_EXIT=${PIPESTATUS[0]};
    log "";
    log "✗ FAILURE: Non-zero data detected (cmp exit code: $CMP_EXIT)";
    
    # Try to find more errors using hexdump on problem areas;
    log "";
    log "Scanning for error locations...";
    
    # Use od to find non-zero bytes (faster than Python);
    sudo od -An -tx1 -v "$DEVICE" | grep -v "^ 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00$" | head -20 | tee -a "$REPORT_FILE" || true;
fi

READ_END=$(date +%s);
READ_DURATION=$((READ_END - READ_START));
READ_SPEED=$((DRIVE_SIZE / READ_DURATION / 1024 / 1024));

log "";
log "Verification completed in $READ_DURATION seconds ($((READ_DURATION / 60)) minutes)";
log "Read speed: ${READ_SPEED} MB/s";
log "";

# PHASE 3: Create filesystem;
log_divider;
log "PHASE 3: Creating new ext4 filesystem";
log_divider;

log "Creating GPT partition table...";
sudo parted -s "$DEVICE" mklabel gpt 2>&1 | tee -a "$REPORT_FILE";

log "Creating partition...";
sudo parted -s "$DEVICE" mkpart primary ext4 0% 100% 2>&1 | tee -a "$REPORT_FILE";

log "Waiting for partition to be recognized...";
sleep 2;
sudo partprobe "$DEVICE" 2>&1 | tee -a "$REPORT_FILE" || true;
sleep 1;

log "Formatting $PARTITION with ext4...";
sudo mkfs.ext4 -F "$PARTITION" 2>&1 | tee -a "$REPORT_FILE";

log "Filesystem created successfully";
log "";

# PHASE 4: Remount;
log_divider;
log "PHASE 4: Remounting drive";
log_divider;

sudo mkdir -p "$MOUNT_POINT";
log "Mounting $PARTITION to $MOUNT_POINT...";
sudo mount "$PARTITION" "$MOUNT_POINT" 2>&1 | tee -a "$REPORT_FILE";

log "Verifying mount...";
mountpoint "$MOUNT_POINT" | tee -a "$REPORT_FILE";

log "Disk usage:";
df -h "$MOUNT_POINT" | tee -a "$REPORT_FILE";
log "";

# Final report;
log_divider;
log "FINAL REPORT";
log_divider;

END_TIME=$(date +%s);
TOTAL_DURATION=$((END_TIME - START_TIME));

log "Total test duration: $TOTAL_DURATION seconds ($((TOTAL_DURATION / 3600)) hours, $(((TOTAL_DURATION % 3600) / 60)) minutes)";
log "Drive tested: $DEVICE";
log "Drive size: $DRIVE_SIZE bytes ($DRIVE_SIZE_HUMAN)";
log "Result: $VERIFY_RESULT";
log "";

if [ "$VERIFY_RESULT" = "SUCCESS" ]; then
    log "✓ The drive passed the test successfully!";
    log "  No errors detected - all bytes verified as zeros";
    EXIT_CODE=0;
else
    log "✗ The drive FAILED the test!";
    log "  Non-zero data was detected during verification";
    log "  This indicates potential drive issues!";
    EXIT_CODE=1;
fi

log "";
log "Full report saved to: $REPORT_FILE";
log_divider;

exit $EXIT_CODE;
