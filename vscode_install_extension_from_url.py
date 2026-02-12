#!/usr/bin/env python3
"""
Install VS Code Extension from URL
===================================

This script installs VS Code / VSCodium extensions manually by cloning from GitHub.
It can accept either a marketplace URL or a direct GitHub URL.

Usage:
    python3 vscode_install_extension_from_url.py <url>
    
Examples:
    python3 vscode_install_extension_from_url.py https://marketplace.visualstudio.com/items?itemName=eliostruyf.vscode-remote-control
    python3 vscode_install_extension_from_url.py https://github.com/estruyf/vscode-remote-control

The script will:
1. Find your VS Code / VSCodium / Antigravity installation
2. Scrape GitHub URL from marketplace page if needed
3. Clone the extension repository to the extensions directory
4. Validate the installation
"""

import json;
import os;
import sys;
import subprocess;
import re;
from pathlib import Path;
from urllib.parse import urlparse, parse_qs;

# Common VS Code/VSCodium/Antigravity installation paths
CANDIDATE_BASE_PATHS = [
    "/usr/lib/antigravity",
    "/usr/share/antigravity",
    "/opt/antigravity",
    "/usr/lib/antigravity-editor",
    "/usr/share/antigravity-editor",
    "/opt/antigravity-editor",
    "/usr/lib/vscodium",
    "/usr/share/vscodium",
    "/opt/vscodium",
    "/usr/lib/code",
    "/usr/share/code",
    "/opt/code",
];

def find_editor_installation():
    """Find the first valid editor installation base path."""
    for base_path in CANDIDATE_BASE_PATHS:
        if os.path.isdir( base_path ):
            return base_path;
    return None;

def find_extensions_directory( base_path ):
    """Find or create the extensions directory for the editor installation."""
    # Try common locations relative to base
    candidates = [
        os.path.join( base_path, "extensions" ),
        os.path.join( base_path, "resources", "app", "extensions" ),
        os.path.join( base_path, "..", "extensions" ),  # Sometimes alongside
    ];
    
    for candidate in candidates:
        normalized = os.path.normpath( candidate );
        if os.path.isdir( normalized ):
            return normalized;
    
    # If none found, create extensions directory at base
    extensions_dir = os.path.join( base_path, "extensions" );
    print( f"📁 Extensions directory not found. Creating at: {extensions_dir}" );
    try:
        os.makedirs( extensions_dir, exist_ok=True );
        return extensions_dir;
    except Exception as e:
        print( f"❌ Failed to create extensions directory: {e}" );
        return None;

def scrape_github_url_from_marketplace( marketplace_url ):
    """Scrape the GitHub repository URL from a marketplace page."""
    try:
        import urllib.request;
        from html.parser import HTMLParser;
        
        class GitHubLinkParser( HTMLParser ):
            def __init__( self ):
                super().__init__();
                self.github_url = None;
            
            def handle_starttag( self, tag, attrs ):
                if tag == "a":
                    for attr, value in attrs:
                        if attr == "href" and "github.com" in value:
                            # Look for repository links (github.com/user/repo or github.com/user/repo/...)
                            if value.count( "/" ) >= 4:  # github.com/user/repo
                                self.github_url = value;
                                return;
        
        print( f"🌐 Fetching marketplace page: {marketplace_url}" );
        with urllib.request.urlopen( marketplace_url ) as response:
            html = response.read().decode( "utf-8" );
        
        parser = GitHubLinkParser();
        parser.feed( html );
        
        if parser.github_url:
            # Clean up the URL
            github_url = parser.github_url;
            if github_url.startswith( "//" ):
                github_url = "https:" + github_url;
            elif github_url.startswith( "/" ):
                github_url = "https://github.com" + github_url;
            
            # Remove trailing slashes and fragments
            github_url = github_url.rstrip( "/" ).split( "#" )[0].split( "?" )[0];
            
            # Extract base repository URL (github.com/user/repo)
            # Remove subpaths like /issues, /pulls, /tree/branch, etc.
            parsed = urlparse( github_url );
            path_parts = parsed.path.strip( "/" ).split( "/" );
            if len( path_parts ) >= 2:
                # Keep only user/repo
                base_path = "/" + "/".join( path_parts[:2] );
                github_url = f"{parsed.scheme}://{parsed.netloc}{base_path}";
            
            print( f"✅ Found GitHub URL: {github_url}" );
            return github_url;
        else:
            print( "❌ Could not find GitHub repository link on marketplace page" );
            return None;
            
    except ImportError:
        print( "❌ urllib.request not available. Cannot scrape marketplace URL." );
        return None;
    except Exception as e:
        print( f"❌ Failed to scrape marketplace page: {e}" );
        return None;

def parse_extension_url( url ):
    """Parse the URL and extract GitHub repository URL if possible."""
    parsed = urlparse( url );
    
    # Check if it's a marketplace URL
    if "marketplace.visualstudio.com" in parsed.netloc:
        return scrape_github_url_from_marketplace( url );
    
    # Check if it's already a GitHub URL
    elif "github.com" in parsed.netloc:
        # Clean up the URL
        github_url = url.rstrip( "/" ).split( "#" )[0].split( "?" )[0];
        return github_url;
    
    else:
        print( f"❌ Unsupported URL format: {url}" );
        print( "Please provide a marketplace.visualstudio.com or github.com URL" );
        return None;

def get_extension_name_from_github_url( github_url ):
    """Extract extension name from GitHub URL."""
    # Example: https://github.com/estruyf/vscode-remote-control
    # Should return: vscode-remote-control
    parsed = urlparse( github_url );
    parts = parsed.path.strip( "/" ).split( "/" );
    
    if len( parts ) >= 2:
        return parts[1];  # repo name
    
    return None;

def clone_extension( github_url, extensions_dir ):
    """Clone the extension repository into the extensions directory."""
    extension_name = get_extension_name_from_github_url( github_url );
    
    if not extension_name:
        print( f"❌ Could not determine extension name from URL: {github_url}" );
        return None;
    
    target_dir = os.path.join( extensions_dir, extension_name );
    
    # Check if already exists
    if os.path.isdir( target_dir ):
        print( f"⚠️  Extension directory already exists: {target_dir}" );
        response = input( "Do you want to remove and re-clone? (y/N): " ).strip().lower();
        if response == "y":
            try:
                import shutil;
                shutil.rmtree( target_dir );
                print( f"🗑️  Removed existing directory" );
            except Exception as e:
                print( f"❌ Failed to remove existing directory: {e}" );
                return None;
        else:
            print( "❌ Installation cancelled" );
            return None;
    
    # Clone the repository
    print( f"📥 Cloning extension from: {github_url}" );
    print( f"📍 Target directory: {target_dir}" );
    
    try:
        result = subprocess.run(
            ["git", "clone", github_url, target_dir],
            capture_output=True,
            text=True,
            check=True
        );
        print( f"✅ Successfully cloned extension to: {target_dir}" );
        return target_dir;
    except subprocess.CalledProcessError as e:
        print( f"❌ Git clone failed: {e.stderr}" );
        return None;
    except FileNotFoundError:
        print( "❌ Git command not found. Please install git." );
        return None;

def build_extension( target_dir ):
    """Build the extension using npm."""
    package_json = os.path.join( target_dir, "package.json" );
    
    if not os.path.isfile( package_json ):
        print( f"⚠️  No package.json found, skipping build" );
        return True;
    
    # Check if extension needs building (has scripts.package or scripts.compile)
    try:
        with open( package_json, "r" ) as f:
            data = json.load( f );
        
        scripts = data.get( "scripts", {} );
        main_file = data.get( "main", "" );
        
        # Check if dist/out directory is needed but doesn't exist
        needs_build = False;
        if "dist/" in main_file or "out/" in main_file:
            build_dir = "dist" if "dist/" in main_file else "out";
            if not os.path.isdir( os.path.join( target_dir, build_dir ) ):
                needs_build = True;
        
        if not needs_build:
            print( f"ℹ️  Extension does not require building" );
            return True;
        
        print( f"🔨 Extension requires building..." );
        
    except Exception as e:
        print( f"⚠️  Could not parse package.json: {e}" );
        print( f"ℹ️  Skipping build step" );
        return True;
    
    # Check if npm is available
    try:
        subprocess.run( ["npm", "--version"], capture_output=True, check=True );
    except ( subprocess.CalledProcessError, FileNotFoundError ):
        print( f"❌ npm is not installed. Cannot build extension." );
        print( f"" );
        print( f"Please install npm (Node.js package manager):" );
        print( f"  sudo pacman -S npm    # CachyOS/Arch" );
        print( f"  sudo apt install npm  # Debian/Ubuntu" );
        print( f"" );
        print( f"After installing npm, run:" );
        print( f"  cd {target_dir}" );
        print( f"  npm install" );
        print( f"  npm run package  # or npm run compile" );
        return False;
    
    # Install dependencies
    print( f"📦 Installing npm dependencies (this may take a while)..." );
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=True
        );
        print( f"✅ Dependencies installed" );
    except subprocess.CalledProcessError as e:
        print( f"❌ npm install failed: {e.stderr}" );
        return False;
    
    # Build the extension
    print( f"🔨 Building extension..." );
    
    # Try different build commands in order of preference
    build_commands = [];
    if "package" in scripts:
        build_commands.append( ["npm", "run", "package"] );
    if "compile" in scripts:
        build_commands.append( ["npm", "run", "compile"] );
    if "build" in scripts:
        build_commands.append( ["npm", "run", "build"] );
    
    if not build_commands:
        print( f"⚠️  No build script found in package.json" );
        print( f"   Looked for: package, compile, build" );
        return False;
    
    for cmd in build_commands:
        try:
            result = subprocess.run(
                cmd,
                cwd=target_dir,
                capture_output=True,
                text=True,
                check=True
            );
            print( f"✅ Extension built successfully using '{cmd[2]}'" );
            return True;
        except subprocess.CalledProcessError as e:
            print( f"⚠️  '{cmd[2]}' failed, trying next..." );
            continue;
    
    print( f"❌ All build commands failed" );
    return False;

def validate_extension( extensions_dir, github_url ):
    """Validate that the extension was installed correctly."""
    extension_name = get_extension_name_from_github_url( github_url );
    target_dir = os.path.join( extensions_dir, extension_name );
    
    # Check for package.json
    package_json = os.path.join( target_dir, "package.json" );
    if not os.path.isfile( package_json ):
        print( f"⚠️  Warning: package.json not found at {package_json}" );
        return False;
    
    # Try to read extension info
    try:
        with open( package_json, "r" ) as f:
            data = json.load( f );
        
        ext_name = data.get( "name", "unknown" );
        ext_version = data.get( "version", "unknown" );
        ext_publisher = data.get( "publisher", "unknown" );
        
        print( f"✅ Extension validated:" );
        print( f"   Name: {ext_name}" );
        print( f"   Version: {ext_version}" );
        print( f"   Publisher: {ext_publisher}" );
        return True;
        
    except Exception as e:
        print( f"⚠️  Could not read package.json: {e}" );
        return False;

def main():
    if len( sys.argv ) < 2:
        print( "Usage: python3 vscode_install_extension_from_url.py <url>" );
        print( "" );
        print( "Examples:" );
        print( "  python3 vscode_install_extension_from_url.py https://marketplace.visualstudio.com/items?itemName=eliostruyf.vscode-remote-control" );
        print( "  python3 vscode_install_extension_from_url.py https://github.com/estruyf/vscode-remote-control" );
        sys.exit( 1 );
    
    url = sys.argv[1];
    
    print( "🔍 Searching for editor installation..." );
    base_path = find_editor_installation();
    
    if not base_path:
        print( "❌ Could not find VS Code / VSCodium / Antigravity installation" );
        print( "Checked paths:" );
        for path in CANDIDATE_BASE_PATHS:
            print( f"  - {path}" );
        print( "\nIf your installation is in a custom location, please edit CANDIDATE_BASE_PATHS in this script." );
        sys.exit( 1 );
    
    print( f"✅ Found editor installation at: {base_path}" );
    
    extensions_dir = find_extensions_directory( base_path );
    if not extensions_dir:
        print( "❌ Could not find or create extensions directory" );
        sys.exit( 1 );
    
    print( f"✅ Extensions directory: {extensions_dir}" );
    
    # Parse the URL to get GitHub repository
    print( f"🔍 Parsing URL: {url}" );
    github_url = parse_extension_url( url );
    
    if not github_url:
        sys.exit( 1 );
    
    # Check if we need sudo (directory is not writable)
    if not os.access( extensions_dir, os.W_OK ):
        print( f"❌ Extensions directory is not writable: {extensions_dir}" );
        print( f"Please run with sudo: sudo python3 {sys.argv[0]} {url}" );
        sys.exit( 1 );
    
    # Clone the extension
    target_dir = clone_extension( github_url, extensions_dir );
    
    if not target_dir:
        sys.exit( 1 );
    
    # Build the extension if needed
    print( "" );
    build_success = build_extension( target_dir );
    
    if not build_success:
        print( "" );
        print( "⚠️  Extension cloned but build failed." );
        print( f"   You may need to build it manually in: {target_dir}" );
    
    # Validate installation
    print( "" );
    validate_extension( extensions_dir, github_url );
    
    print( "" );
    if build_success:
        print( "🚀 Installation complete! Please restart your editor for changes to take effect." );
    else:
        print( "⚠️  Extension installed but may not work until built successfully." );

if __name__ == "__main__":
    main();
