#!/usr/bin/env python3
"""
Export WiFi passwords from NetworkManager on Linux
"""

import os;
import sys;
import re;
from pathlib import Path;
import configparser;


def get_wifi_profiles():
    """Get all WiFi profiles from NetworkManager"""
    nm_path = Path( "/etc/NetworkManager/system-connections" );
    
    if not nm_path.exists():
        print( f"Error: NetworkManager path not found: {nm_path}", file=sys.stderr );
        return [];
    
    profiles = [];
    
    for conn_file in nm_path.glob( "*" ):
        if conn_file.is_file():
            try:
                config = configparser.ConfigParser();
                config.read( conn_file );
                
                # Check if it's a WiFi connection
                if config.has_section( "wifi" ) or config.has_section( "802-11-wireless" ):
                    ssid = None;
                    password = None;
                    
                    # Get SSID
                    if config.has_option( "wifi", "ssid" ):
                        ssid = config.get( "wifi", "ssid" );
                    elif config.has_option( "802-11-wireless", "ssid" ):
                        ssid = config.get( "802-11-wireless", "ssid" );
                    
                    # Get password
                    if config.has_section( "wifi-security" ):
                        if config.has_option( "wifi-security", "psk" ):
                            password = config.get( "wifi-security", "psk" );
                    elif config.has_section( "802-11-wireless-security" ):
                        if config.has_option( "802-11-wireless-security", "psk" ):
                            password = config.get( "802-11-wireless-security", "psk" );
                    
                    if ssid:
                        profiles.append( {
                            "ssid": ssid,
                            "password": password if password else "(no password or encrypted)",
                            "file": conn_file.name
                        } );
            
            except Exception as e:
                print( f"Warning: Could not read {conn_file.name}: {e}", file=sys.stderr );
    
    return profiles;


def main():
    if os.geteuid() != 0:
        print( "Error: This script requires root privileges to read WiFi passwords." );
        print( "Run with: sudo python3 export_wifi_passwords.py" );
        sys.exit( 1 );
    
    profiles = get_wifi_profiles();
    
    if not profiles:
        print( "No WiFi profiles found." );
        return;
    
    print( f"Found {len( profiles )} WiFi profile(s):\n" );
    print( f"{'SSID':<30} {'Password':<30} {'File':<30}" );
    print( "=" * 90 );
    
    for profile in profiles:
        print( f"{profile['ssid']:<30} {profile['password']:<30} {profile['file']:<30}" );


if __name__ == "__main__":
    main();
