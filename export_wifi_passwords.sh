#!/bin/bash
#
# Export WiFi passwords from NetworkManager on Linux
#

NM_PATH="/etc/NetworkManager/system-connections"

if [ "$EUID" -ne 0 ]; then
    echo "Error: This script requires root privileges to read WiFi passwords."
    echo "Run with: sudo bash export_wifi_passwords.sh"
    exit 1
fi

if [ ! -d "$NM_PATH" ]; then
    echo "Error: NetworkManager path not found: $NM_PATH"
    exit 1
fi

echo "WiFi Profiles:"
echo "============================================"
echo ""

count=0

for file in "$NM_PATH"/*; do
    if [ -f "$file" ]; then
        # Check if it's a WiFi connection
        if grep -q "type=wifi" "$file" 2>/dev/null || grep -q "\[wifi\]" "$file" 2>/dev/null || grep -q "\[802-11-wireless\]" "$file" 2>/dev/null; then
            ssid=$( grep -E "^ssid=" "$file" | cut -d'=' -f2- )
            password=$( grep -E "^psk=" "$file" | cut -d'=' -f2- )
            
            if [ -z "$password" ]; then
                password="(no password or encrypted)"
            fi
            
            if [ -n "$ssid" ]; then
                echo "SSID:     $ssid"
                echo "Password: $password"
                echo "File:     $(basename "$file")"
                echo ""
                count=$((count + 1))
            fi
        fi
    fi
done

if [ $count -eq 0 ]; then
    echo "No WiFi profiles found."
else
    echo "Found $count WiFi profile(s)"
fi
