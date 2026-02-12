#!/usr/bin/env python3
"""
Restore VS Code / VSCodium Marketplace Settings
===============================================

This script modifies the `product.json` configuration file of your VS Code or VSCodium
installation to use the official Microsoft Visual Studio Marketplace.

This is useful if you are using VSCodium but want access to the full range of
extensions available in the official marketplace (e.g. Pylance, Remote-SSH).

Usage:
    sudo python3 scripts/restore_marketplace.py

The script will:
1. Search for `product.json` in common Linux installation paths.
2. Create a backup of the existing `product.json`.
3. Update the `extensionsGallery` section with Microsoft's official URLs.
"""

import json
import os
import sys
import shutil
from datetime import datetime

# Common installation paths for VS Code and VSCodium on Linux
CANDIDATE_PATHS = [
    "/usr/share/vscodium/resources/app/product.json",
    "/opt/vscodium/resources/app/product.json",
    "/usr/share/code/resources/app/product.json",
    "/usr/lib/vscodium/resources/app/product.json",
    "/usr/lib/code/resources/app/product.json",
    # Flatpak paths (might be read-only, but usually accessible via hostfs if mounted properly, though direct edit is tricky)
    # listing anyway for visibility
    "/var/lib/flatpak/app/com.vscodium.codium/current/active/files/share/vscodium/resources/app/product.json",
    
    # Antigravity Editor Paths (presumed structure)
    "/usr/lib//antigravity/product.json",
    "/usr/share/antigravity/resources/app/product.json",
    "/opt/antigravity/resources/app/product.json",
    "/usr/lib/antigravity/resources/app/product.json",
    "/usr/share/antigravity-editor/resources/app/product.json",
    "/opt/antigravity-editor/resources/app/product.json",
]

# Official Microsoft Marketplace Configuration
MICROSOFT_MARKETPLACE = {
    "serviceUrl": "https://marketplace.visualstudio.com/_apis/public/gallery",
    "cacheUrl": "https://vscode.blob.core.windows.net/gallery/index",
    "itemUrl": "https://marketplace.visualstudio.com/items",
    "controlUrl": "https://az764295.vo.msecnd.net/extensions/",
    "recommendationsUrl": "https://az764295.vo.msecnd.net/extensions/workspaceRecommendations.json.gz"
}

def find_product_json():
    """Find the first valid product.json from CANDIDATE_PATHS."""
    for path in CANDIDATE_PATHS:
        # Check if we can read the file
        if os.path.isfile(path):
            return path
    return None

def main():
    if os.geteuid() != 0:
        print("❌ Error: This script must be run as root (sudo) to modify system files.")
        print(f"Usage: sudo {sys.executable} {os.path.abspath(__file__)}")
        # Check if running in a virtual environment
        if sys.prefix != sys.base_prefix:
             print("Note: If using 'sudo', ensure you are using the system python or the correct virtualenv binary.")
        sys.exit(1)

    print("🔍 Searching for product.json...")
    target_file = find_product_json()

    if not target_file:
        print("❌ Could not find product.json in standard locations.")
        print("Checked paths:")
        for path in CANDIDATE_PATHS:
            print(f"  - {path}")
        print("\nIf your installation is in a custom location, please edit CANDIDATE_PATHS in this script.")
        sys.exit(1)

    print(f"✅ Found product.json at: {target_file}")

    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{target_file}.backup_{timestamp}"
    
    try:
        shutil.copy2(target_file, backup_file)
        print(f"📦 Backup created at: {backup_file}")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        sys.exit(1)

    # Read and update product.json
    try:
        with open(target_file, "r") as f:
            data = json.load(f)
        
        print(f"🔧 Updating extensionsGallery configuration in {target_file}...")
        
        if "extensionsGallery" not in data:
            data["extensionsGallery"] = {}
        
        # Update with Microsoft marketplace settings
        for key, value in MICROSOFT_MARKETPLACE.items():
            data["extensionsGallery"][key] = value

        # Write back to file
        with open(target_file, "w") as f:
            json.dump(data, f, indent="\t")
        
        print("✅ Successfully updated product.json!")
        print("🚀 Please restart VS Code / VSCodium for changes to take effect.")

    except Exception as e:
        print(f"❌ Failed to update product.json: {e}")
        print("attempting to restore backup...")
        # Try to restore backup
        try:
            if os.path.exists(backup_file):
                shutil.copy2(backup_file, target_file)
                print("↺ Restored original file from backup.")
            else:
                print("!! CRITICAL: Backup file not found. Manual intervention required.")
        except Exception as restore_error:
            print(f"!! CRITICAL: Failed to restore backup: {restore_error}. Manual intervention required.")
        sys.exit(1)

if __name__ == "__main__":
    main()
