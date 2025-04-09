# Requires administrative privileges to run properly
# Save this as Export-WiFiNetworkKeys.ps1

function Export-WiFiNetworkKeys {
    [CmdletBinding()]
    param (
        [string]$OutputPath = "$env:USERPROFILE\Documents\WiFi_Profiles_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"
    )

    Write-Host "Starting WiFi network key export..." -ForegroundColor Cyan
    
    # Check for administrative privileges
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
    if (-not $isAdmin) {
        Write-Warning "This script requires administrative privileges to retrieve all network keys."
        Write-Warning "Please run this script as Administrator for complete results."
    }

    # Get all WiFi profiles
    try {
        $profiles = netsh wlan show profiles | Select-String "All User Profile" | ForEach-Object { $_.ToString().Split(':')[1].Trim() }
        
        if ($profiles.Count -eq 0) {
            Write-Warning "No WiFi profiles found on this computer."
            return
        }
        
        Write-Host "Found $($profiles.Count) WiFi profiles." -ForegroundColor Green
        
        # Prepare the output file
        "WiFi Network Profiles Export - $(Get-Date)" | Out-File -FilePath $OutputPath -Force
        "==================================================" | Out-File -FilePath $OutputPath -Append
        
        # Process each profile
        foreach ($profile in $profiles) {
            Write-Host "Processing profile: $profile" -ForegroundColor Yellow
            
            $profileInfo = netsh wlan show profile name="$profile" key=clear
            
            # Extract SSID
            $ssid = $profile
            
            # Extract Security Key
            $securityKey = $profileInfo | Select-String "Key Content" 
            if ($securityKey) {
                $password = $securityKey.ToString().Split(':')[1].Trim()
            } else {
                $password = "No security key found (Open network or unable to retrieve)"
            }
            
            # Extract Authentication
            $authentication = $profileInfo | Select-String "Authentication" | Select-Object -First 1
            if ($authentication) {
                $authType = $authentication.ToString().Split(':')[1].Trim()
            } else {
                $authType = "Unknown"
            }
            
            # Extract Encryption
            $encryption = $profileInfo | Select-String "Cipher" | Select-Object -First 1
            if ($encryption) {
                $encryptionType = $encryption.ToString().Split(':')[1].Trim()
            } else {
                $encryptionType = "Unknown"
            }
            
            # Write to output file
            "Network: $ssid" | Out-File -FilePath $OutputPath -Append
            "Password: $password" | Out-File -FilePath $OutputPath -Append 
            "Authentication: $authType" | Out-File -FilePath $OutputPath -Append
            "Encryption: $encryptionType" | Out-File -FilePath $OutputPath -Append
            "==================================================" | Out-File -FilePath $OutputPath -Append
        }
        
        Write-Host "Export completed successfully!" -ForegroundColor Green
        Write-Host "WiFi profiles have been exported to: $OutputPath" -ForegroundColor Cyan
    }
    catch {
        Write-Error "An error occurred while exporting WiFi profiles: $_"
    }
}

# Execute the function
Export-WiFiNetworkKeys