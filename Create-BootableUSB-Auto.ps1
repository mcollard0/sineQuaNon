param(
    [Parameter(Mandatory=$false)]
    [string]$DriveLetter = "",
    
    [Parameter(Mandatory=$false)]
    [string]$IsoPath = "C:\temp\ubuntu-25.04-desktop-amd64.iso"
)

# Ensure running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

Write-Host "=== Bootable USB Creator ===" -ForegroundColor Cyan
Write-Host "ISO Path: $IsoPath" -ForegroundColor Yellow
Write-Host ""

# Validate ISO file exists
if (-not (Test-Path $IsoPath)) {
    Write-Host "ERROR: ISO file not found at: $IsoPath" -ForegroundColor Red
    exit 1
}

function Get-USBDrives {
    Write-Host "Scanning for USB drives..." -ForegroundColor Green
    
    $usbDrives = @()
    
    # Get all USB disks using modern PowerShell method
    try {
        $usbDisks = Get-Disk | Where-Object { $_.BusType -eq "USB" }
        
        foreach ($disk in $usbDisks) {
            try {
                $partitions = Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue
                
                foreach ($partition in $partitions) {
                    if ($partition.DriveLetter) {
                        $driveLetter = $partition.DriveLetter
                        $driveLetterWithColon = "${driveLetter}:"
                        
                        # Get additional info from WMI
                        $logicalDisk = Get-WmiObject -Class Win32_LogicalDisk -Filter "DeviceID='$driveLetterWithColon'"
                        
                        if ($logicalDisk) {
                            $usbDrive = [PSCustomObject]@{
                                DiskNumber = $disk.Number
                                DriveLetter = $driveLetter
                                DriveLetterWithColon = $driveLetterWithColon
                                FriendlyName = $disk.FriendlyName.Trim()
                                FileSystem = $logicalDisk.FileSystem
                                Label = $logicalDisk.VolumeName
                                SizeGB = [math]::Round($logicalDisk.Size / 1GB, 2)
                                FreeSpaceGB = [math]::Round($logicalDisk.FreeSpace / 1GB, 2)
                                HealthStatus = $disk.HealthStatus
                                PartitionStyle = $disk.PartitionStyle
                            }
                            $usbDrives += $usbDrive
                        }
                    }
                }
            } catch {
                Write-Host "  Warning: Could not get partition info for disk $($disk.Number)" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "ERROR: Could not enumerate USB drives using modern method. Falling back to WMI..." -ForegroundColor Yellow
        
        # Fallback to WMI method
        try {
            $wmiDisks = Get-WmiObject -Class Win32_DiskDrive | Where-Object { $_.InterfaceType -eq "USB" -or $_.PNPDeviceID -like "*USB*" }
            
            foreach ($wmiDisk in $wmiDisks) {
                # This is more complex with WMI - for now, show that USB drives were found but modern method failed
                Write-Host "  Found USB disk: $($wmiDisk.Model) but could not get drive letter info" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "ERROR: Could not enumerate USB drives with either method" -ForegroundColor Red
        }
    }
    
    return $usbDrives
}

function Show-USBDriveMenu {
    param([array]$drives)
    
    Write-Host ""
    Write-Host "=== Available USB Drives ===" -ForegroundColor Cyan
    Write-Host ""
    
    for ($i = 0; $i -lt $drives.Length; $i++) {
        $drive = $drives[$i]
        $index = $i + 1
        
        Write-Host "[$index] Drive $($drive.DriveLetterWithColon)" -ForegroundColor White
        Write-Host "    Device: $($drive.FriendlyName)" -ForegroundColor Gray
        Write-Host "    Label: $($drive.Label)" -ForegroundColor Gray
        Write-Host "    File System: $($drive.FileSystem)" -ForegroundColor Gray
        Write-Host "    Size: $($drive.SizeGB) GB" -ForegroundColor Gray
        Write-Host "    Free Space: $($drive.FreeSpaceGB) GB" -ForegroundColor Gray
        Write-Host "    Health: $($drive.HealthStatus)" -ForegroundColor Gray
        Write-Host ""
    }
    
    do {
        $choice = Read-Host "Select USB drive (1-$($drives.Length)) or 'q' to quit"
        
        if ($choice -eq 'q' -or $choice -eq 'Q') {
            Write-Host "Operation cancelled." -ForegroundColor Yellow
            exit 0
        }
        
        try {
            $choiceNum = [int]$choice
            if ($choiceNum -ge 1 -and $choiceNum -le $drives.Length) {
                return $drives[$choiceNum - 1]
            } else {
                Write-Host "Invalid choice. Please enter a number between 1 and $($drives.Length)." -ForegroundColor Red
            }
        } catch {
            Write-Host "Invalid input. Please enter a number between 1 and $($drives.Length) or 'q' to quit." -ForegroundColor Red
        }
    } while ($true)
}

# Get USB drives
$usbDrives = Get-USBDrives

if ($usbDrives.Length -eq 0) {
    Write-Host "ERROR: No USB drives found!" -ForegroundColor Red
    Write-Host "Please connect a USB drive and try again." -ForegroundColor Red
    exit 1
}

# Determine which USB drive to use
$selectedDrive = $null

if ($DriveLetter -ne "") {
    # User specified a drive letter, validate it's USB
    $DriveLetter = $DriveLetter.TrimEnd(':')
    $specifiedDrive = $usbDrives | Where-Object { $_.DriveLetter -eq $DriveLetter }
    
    if ($specifiedDrive) {
        Write-Host "Using specified USB drive: $($DriveLetter):" -ForegroundColor Green
        $selectedDrive = $specifiedDrive
    } else {
        Write-Host "ERROR: Drive $($DriveLetter): is not a USB drive or not found!" -ForegroundColor Red
        Write-Host "Available USB drives:" -ForegroundColor Yellow
        foreach ($drive in $usbDrives) {
            Write-Host "  $($drive.DriveLetterWithColon) - $($drive.FriendlyName)" -ForegroundColor Gray
        }
        exit 1
    }
} elseif ($usbDrives.Length -eq 1) {
    # Only one USB drive found, use it automatically
    $selectedDrive = $usbDrives[0]
    Write-Host "Found single USB drive: $($selectedDrive.DriveLetterWithColon) ($($selectedDrive.FriendlyName))" -ForegroundColor Green
    Write-Host "Automatically selecting this drive." -ForegroundColor Green
} else {
    # Multiple USB drives found, let user choose
Write-Host "Found $($usbDrives.Length) USB drive(s)." -ForegroundColor Green
    $selectedDrive = Show-USBDriveMenu -drives $usbDrives
}

# Display selected drive information
Write-Host ""
Write-Host "=== Selected Drive Information ===" -ForegroundColor Cyan
Write-Host "Drive Letter: $($selectedDrive.DriveLetterWithColon)" -ForegroundColor White
Write-Host "Device: $($selectedDrive.FriendlyName)" -ForegroundColor White
Write-Host "Label: $($selectedDrive.Label)" -ForegroundColor White
Write-Host "File System: $($selectedDrive.FileSystem)" -ForegroundColor White
Write-Host "Total Size: $($selectedDrive.SizeGB) GB" -ForegroundColor White
Write-Host "Free Space: $($selectedDrive.FreeSpaceGB) GB" -ForegroundColor White
Write-Host "Health Status: $($selectedDrive.HealthStatus)" -ForegroundColor White
Write-Host "Disk Number: $($selectedDrive.DiskNumber)" -ForegroundColor White

# Check if drive is FAT32
if ($selectedDrive.FileSystem -ne "FAT32") {
    Write-Host ""
    Write-Host "ERROR: Drive $($selectedDrive.DriveLetterWithColon) is not formatted as FAT32!" -ForegroundColor Red
    Write-Host "Current file system: $($selectedDrive.FileSystem)" -ForegroundColor Red
    Write-Host "This script requires a FAT32 formatted USB drive." -ForegroundColor Red
    Write-Host "OPERATION ABORTED!" -ForegroundColor Red
    exit 1
}

# Try to list files on the drive
Write-Host ""
Write-Host "=== Current Drive Contents ===" -ForegroundColor Cyan
try {
    $Items = Get-ChildItem -Path $selectedDrive.DriveLetterWithColon -Force -ErrorAction Stop
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
    Write-Host "Drive size: $($selectedDrive.SizeGB) GB" -ForegroundColor Gray
}

# ISO file information
Write-Host ""
Write-Host "=== ISO Information ===" -ForegroundColor Cyan
$IsoSize = (Get-Item $IsoPath).Length
$IsoSizeGB = [math]::Round($IsoSize / 1GB, 2)
Write-Host "ISO Path: $IsoPath" -ForegroundColor White
Write-Host "ISO Size: $IsoSizeGB GB" -ForegroundColor White

# Check if ISO will fit on USB drive
$AvailableSpace = ($selectedDrive.SizeGB * 1GB) * 0.95  # Account for formatting overhead
if ($IsoSize -gt $AvailableSpace) {
    Write-Host ""
    $AvailableSpaceGB = [math]::Round($AvailableSpace / 1GB, 2)
    Write-Host "ERROR: ISO file ($IsoSizeGB GB) is larger than USB drive available space ($AvailableSpaceGB GB)!" -ForegroundColor Red
    exit 1
}

# Final confirmation with timeout
Write-Host ""
Write-Host "=== FINAL WARNING ===" -ForegroundColor Red
Write-Host "This will completely erase drive $($selectedDrive.DriveLetterWithColon) and create a bootable Ubuntu USB!" -ForegroundColor Red
Write-Host "Selected USB Device: $($selectedDrive.FriendlyName)" -ForegroundColor Red
Write-Host ""
Write-Host "Press ANY KEY to continue or wait 30 seconds to abort..." -ForegroundColor Yellow

# Timeout implementation
$timeout = 30
$startTime = Get-Date
$keyPressed = $false

while (((Get-Date) - $startTime).TotalSeconds -lt $timeout -and -not $keyPressed) {
    if ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true)
        Write-Host "Key pressed, continuing..." -ForegroundColor Green
        $keyPressed = $true
        break
    }
    $remaining = $timeout - [math]::Floor(((Get-Date) - $startTime).TotalSeconds)
    Write-Host "`rTimeout in $remaining seconds..." -NoNewline -ForegroundColor Yellow
    Start-Sleep -Milliseconds 100
}

if (-not $keyPressed) {
    Write-Host ""
    Write-Host "Timeout reached. Operation aborted." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host ""

# Execute diskpart operations to create bootable USB
Write-Host "=== CREATING BOOTABLE USB ===" -ForegroundColor Magenta
Write-Host "Formatting disk $($selectedDrive.DiskNumber) as FAT32..." -ForegroundColor Green
Write-Host "This will take a moment..." -ForegroundColor Yellow

# Create diskpart script and execute USB creation
$diskpartScript = "select disk $($selectedDrive.DiskNumber)`nclean`ncreate partition primary`nselect partition 1`nactive`nformat fs=fat32 quick label=UBUNTU_BOOT`nassign letter=$($selectedDrive.DriveLetter)`nexit"
$scriptPath = "$env:TEMP\diskpart_script.txt"
$diskpartScript | Out-File -FilePath $scriptPath -Encoding ASCII

Write-Host "Running diskpart to format USB drive..." -ForegroundColor Green
diskpart /s $scriptPath

# Mount ISO and copy contents
Write-Host "Mounting ISO..." -ForegroundColor Green
$mountResult = Mount-DiskImage -ImagePath $IsoPath -PassThru
$isoDriveLetter = ($mountResult | Get-Volume).DriveLetter

Write-Host "Copying files from $($isoDriveLetter): to $($selectedDrive.DriveLetterWithColon)" -ForegroundColor Green
robocopy "$($isoDriveLetter):\" "$($selectedDrive.DriveLetterWithColon)\" /E /R:1 /W:1

# Dismount ISO
Dismount-DiskImage -ImagePath $IsoPath

# Clean up
Remove-Item $scriptPath

Write-Host ""
Write-Host "Bootable USB creation complete!" -ForegroundColor Green

Write-Host ""
Write-Host "Bootable USB creation process completed!" -ForegroundColor Green
Write-Host "USB Drive: $($selectedDrive.DriveLetterWithColon) ($($selectedDrive.FriendlyName)) is now bootable!" -ForegroundColor Green
Write-Host "You can now safely eject the USB drive and use it to boot Ubuntu." -ForegroundColor Cyan
