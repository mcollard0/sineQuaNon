param(
    [Parameter(Mandatory=$true)]
    [string]$DriveLetter,
    
    [Parameter(Mandatory=$false)]
    [string]$IsoPath = "C:\temp\ubuntu-25.04-desktop-amd64.iso"
)

# Ensure running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

Write-Host "=== Bootable USB Creator ===" -ForegroundColor Cyan
Write-Host "Drive Letter: $DriveLetter" -ForegroundColor Yellow
Write-Host "ISO Path: $IsoPath" -ForegroundColor Yellow
Write-Host ""

# Validate ISO file exists
if (-not (Test-Path $IsoPath)) {
    Write-Host "ERROR: ISO file not found at: $IsoPath" -ForegroundColor Red
    exit 1
}

# Normalize drive letter (remove colon if present, add colon for consistency)
$DriveLetter = $DriveLetter.TrimEnd(':')
$DriveLetterWithColon = "${DriveLetter}:"

Write-Host "Checking drive $DriveLetterWithColon..." -ForegroundColor Green

# Get the logical disk information
try {
    $LogicalDisk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$DriveLetterWithColon'"
    if (-not $LogicalDisk) {
        Write-Host "ERROR: Drive $DriveLetterWithColon not found!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Failed to get drive information: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Get physical disk information to verify USB connection
try {
    $Partition = Get-WmiObject -Class Win32_LogicalDiskToPartition | Where-Object { $_.Dependent -like "*$DriveLetter*" }
    if (-not $Partition) {
        Write-Host "ERROR: Could not find partition information for drive $DriveLetterWithColon" -ForegroundColor Red
        exit 1
    }
    
    $DiskDrive = Get-WmiObject -Class Win32_DiskDriveToDiskPartition | Where-Object { $_.Dependent -eq $Partition.Antecedent }
    if (-not $DiskDrive) {
        Write-Host "ERROR: Could not find disk drive information" -ForegroundColor Red
        exit 1
    }
    
    $PhysicalDisk = Get-WmiObject -Class Win32_DiskDrive | Where-Object { $_.DeviceID -eq $DiskDrive.Antecedent.Split('=')[1].Trim('"') }
    if (-not $PhysicalDisk) {
        Write-Host "ERROR: Could not find physical disk information" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "ERROR: Failed to get physical disk information: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# CRITICAL SAFETY CHECK: Verify this is a USB device
Write-Host "Verifying USB connection..." -ForegroundColor Yellow
$IsUSB = $false

# Check multiple indicators for USB connection
if ($PhysicalDisk.InterfaceType -eq "USB") {
    $IsUSB = $true
    Write-Host "✓ Interface Type: USB" -ForegroundColor Green
} elseif ($PhysicalDisk.PNPDeviceID -like "*USB*") {
    $IsUSB = $true
    Write-Host "✓ PNP Device ID indicates USB connection" -ForegroundColor Green
} elseif ($PhysicalDisk.Model -like "*USB*") {
    $IsUSB = $true
    Write-Host "✓ Model name indicates USB device" -ForegroundColor Green
} else {
    # Additional check using Get-Disk if available (newer PowerShell)
    try {
        $ModernDisk = Get-Disk | Where-Object { $_.Number -eq $PhysicalDisk.Index }
        if ($ModernDisk -and $ModernDisk.BusType -eq "USB") {
            $IsUSB = $true
            Write-Host "✓ Bus Type: USB" -ForegroundColor Green
        }
    } catch {
        # Get-Disk cmdlet not available, continue with other checks
    }
}

if (-not $IsUSB) {
    Write-Host ""
    Write-Host "CRITICAL ERROR: Drive $DriveLetterWithColon does not appear to be a USB device!" -ForegroundColor Red
    Write-Host "Interface Type: $($PhysicalDisk.InterfaceType)" -ForegroundColor Red
    Write-Host "Model: $($PhysicalDisk.Model)" -ForegroundColor Red
    Write-Host "PNP Device ID: $($PhysicalDisk.PNPDeviceID)" -ForegroundColor Red
    Write-Host ""
    Write-Host "OPERATION ABORTED FOR SAFETY!" -ForegroundColor Red
    exit 1
}

# Check if drive is FAT32
Write-Host "Checking file system..." -ForegroundColor Yellow
if ($LogicalDisk.FileSystem -ne "FAT32") {
    Write-Host ""
    Write-Host "ERROR: Drive $DriveLetterWithColon is not formatted as FAT32!" -ForegroundColor Red
    Write-Host "Current file system: $($LogicalDisk.FileSystem)" -ForegroundColor Red
    Write-Host "This script requires a FAT32 formatted USB drive." -ForegroundColor Red
    Write-Host "OPERATION ABORTED!" -ForegroundColor Red
    exit 1
} else {
    Write-Host "✓ File System: FAT32" -ForegroundColor Green
}

# Display drive information
Write-Host ""
Write-Host "=== Drive Information ===" -ForegroundColor Cyan
Write-Host "Drive Letter: $DriveLetterWithColon" -ForegroundColor White
Write-Host "Label: $($LogicalDisk.VolumeName)" -ForegroundColor White
Write-Host "File System: $($LogicalDisk.FileSystem)" -ForegroundColor White
$SizeGB = [math]::Round($LogicalDisk.Size / 1GB, 2)
$FreeSpaceGB = [math]::Round($LogicalDisk.FreeSpace / 1GB, 2)
Write-Host "Total Size: $SizeGB GB" -ForegroundColor White
Write-Host "Free Space: $FreeSpaceGB GB" -ForegroundColor White
Write-Host "Device Model: $($PhysicalDisk.Model)" -ForegroundColor White
Write-Host "Interface: $($PhysicalDisk.InterfaceType)" -ForegroundColor White

# Try to list files on the drive
Write-Host ""
Write-Host "=== Current Drive Contents ===" -ForegroundColor Cyan
try {
    $Items = Get-ChildItem -Path $DriveLetterWithColon -Force -ErrorAction Stop
    if ($Items.Count -eq 0) {
        Write-Host "Drive is empty." -ForegroundColor Gray
    } else {
        Write-Host "Files and folders on drive:" -ForegroundColor White
        $Items | ForEach-Object {
            $Size = if ($_.PSIsContainer) { "<DIR>" } else { "$([math]::Round($_.Length / 1MB, 2)) MB" }
            Write-Host "  $($_.Name) - $Size" -ForegroundColor Gray
        }
        Write-Host ""
        Write-Host "WARNING: All existing files will be deleted!" -ForegroundColor Red
    }
} catch {
    Write-Host "Could not read drive contents: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Drive size: $SizeGB GB" -ForegroundColor Gray
}

# Get disk number for diskpart operations
$DiskNumber = $PhysicalDisk.Index
Write-Host ""
Write-Host "Physical Disk Number: $DiskNumber" -ForegroundColor Yellow

# ISO file information
Write-Host ""
Write-Host "=== ISO Information ===" -ForegroundColor Cyan
$IsoSize = (Get-Item $IsoPath).Length
$IsoSizeGB = [math]::Round($IsoSize / 1GB, 2)
Write-Host "ISO Path: $IsoPath" -ForegroundColor White
Write-Host "ISO Size: $IsoSizeGB GB" -ForegroundColor White

# Check if ISO will fit on USB drive
$AvailableSpace = $LogicalDisk.Size * 0.95  # Account for formatting overhead
if ($IsoSize -gt $AvailableSpace) {
    Write-Host ""
    $AvailableSpaceGB = [math]::Round($AvailableSpace / 1GB, 2)
    Write-Host "ERROR: ISO file ($IsoSizeGB GB) is larger than USB drive available space ($AvailableSpaceGB GB)!" -ForegroundColor Red
    exit 1
}

# Final confirmation with timeout
Write-Host ""
Write-Host "=== FINAL WARNING ===" -ForegroundColor Red
Write-Host "This will completely erase drive $DriveLetterWithColon and create a bootable Ubuntu USB!" -ForegroundColor Red
Write-Host ""
Write-Host "Press ANY KEY to continue or wait 30 seconds to abort..." -ForegroundColor Yellow

# Timeout implementation
$timeout = 30
$startTime = Get-Date
while (((Get-Date) - $startTime).TotalSeconds -lt $timeout) {
    if ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true)
        Write-Host "Key pressed, continuing..." -ForegroundColor Green
        break
    }
    $remaining = $timeout - [math]::Floor(((Get-Date) - $startTime).TotalSeconds)
    Write-Host "`rTimeout in $remaining seconds..." -NoNewline -ForegroundColor Yellow
    Start-Sleep -Milliseconds 100
}

if (((Get-Date) - $startTime).TotalSeconds -ge $timeout) {
    Write-Host ""
    Write-Host "Timeout reached. Operation aborted." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ""

# TODO: Uncomment these sections after testing the detection logic
Write-Host "=== DISKPART OPERATIONS (COMMENTED OUT FOR TESTING) ===" -ForegroundColor Magenta

Write-Host "Would create diskpart script for disk $DiskNumber..." -ForegroundColor Gray
Write-Host "Would format as FAT32..." -ForegroundColor Gray
Write-Host "Would mount and copy ISO contents..." -ForegroundColor Gray

Write-Host ""
Write-Host "Detection and safety checks completed successfully!" -ForegroundColor Green
Write-Host "Uncomment the diskpart section to enable actual USB formatting." -ForegroundColor Yellow
