# Convert binary file to hex bytes in 0xFF format
param(
    [string]$InputFile,      # Binary file to read
    [string]$OutputFile = "" # Optional output file
)

# Read the binary file
$bytes = [System.IO.File]::ReadAllBytes($InputFile)

# Convert bytes to hex format (0xFF)
$hexString = ($bytes | ForEach-Object { "0x{0:X2}" -f $_ }) -join ", "

# Print to console or write to file
if ($OutputFile -ne "") {
    $hexString | Out-File -Encoding utf8 $OutputFile
    Write-Output "Hex data written to $OutputFile"
} else {
    Write-Output $hexString
}