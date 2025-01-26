param (
    [Parameter(Mandatory=$true)]
    [string]$fileName,
    
    [Parameter(Mandatory=$true)]
    [int]$samplePercent,
    
    [Parameter(Mandatory=$false)]
    [string]$outputFolder = "dump"
)

# Validate percentage
if ($samplePercent -lt 1 -or $samplePercent -gt 100) {
    Write-Error "Percentage must be between 1 and 100"
    exit 1
}

# Create or verify output folder
if (-not (Test-Path -Path $outputFolder)) {
    Write-Host "Creating output folder: $outputFolder"
    New-Item -ItemType Directory -Path $outputFolder | Out-Null
}
else {
    Write-Host "Using existing folder: $outputFolder"
}

# Get file extension
$extension = [System.IO.Path]::GetExtension($fileName)
$baseFileName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)

# Get all commits for the file
$commits = git log --follow --format="%H|%ad" --date=format:"%Y%m%d_%H%M%S" -- $fileName
$commitArray = $commits -split "`n"

# Calculate number of commits to sample
$totalCommits = $commitArray.Count
$samplesToTake = [math]::Ceiling(($totalCommits * $samplePercent) / 100)

Write-Host "Total commits: $totalCommits"
Write-Host "Taking $samplesToTake samples"

# Calculate step size to evenly distribute samples
$stepSize = $totalCommits / $samplesToTake

# Process commits
for ($i = 0; $i -lt $totalCommits; $i += $stepSize) {
    $index = [math]::Floor($i)
    $commit = $commitArray[$index]
    
    if ($commit -match "([^|]+)\|(.+)") {
        $hash = $matches[1]
        $date = $matches[2]
        
        # Create new filename with full path
        $newFileName = Join-Path -Path $outputFolder -ChildPath "${baseFileName}_${date}_${hash}${extension}"
        
        # Checkout file from this commit
        git show "$hash`:$fileName" > $newFileName
        
        # Check if file is empty (0 bytes)
        if ((Get-Item $newFileName).Length -eq 0) {
            Remove-Item $newFileName
            Write-Host "Deleted empty file: $newFileName"
            continue
        }

        # Convert date string to DateTime object
        # Date format is "YYYYMMDD_HHMMSS"
        $dateTime = [DateTime]::ParseExact($date, "yyyyMMdd_HHmmss", $null)
        
        # Set both LastWriteTime and CreationTime
        (Get-Item $newFileName).LastWriteTime = $dateTime
        (Get-Item $newFileName).CreationTime = $dateTime
        
        Write-Host "Created $newFileName with timestamp $dateTime"
    }
}