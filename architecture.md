# SinaQuaNon Repository Architecture

## Overview

SinaQuaNon is a mixed-purpose programming repository containing utilities, scripts, and tools for various tasks including medical data processing, system administration, and development workflows.

## Repository Structure

### Core Tools
- **`sql2mongo.py`** - Database migration utility for converting SQL data to MongoDB
- **`sqlq.py`** - SQL query execution utility 
- **`ssd_scraper.py`** - SSD price and specification scraper
- **`KC New Restaurants.py`** - Kansas City restaurant discovery tool

### PowerShell Scripts
- **`Create-BootableUSB.ps1`** - Creates bootable USB drives
- **`ExportWifiPasswords.ps1`** - Exports saved WiFi credentials
- **`GitFileDump.ps1`** - Git repository file extraction utility

### HL7 Medical Messaging Tools (`HL7/`)

The HL7 directory contains a complete suite for HL7 v2.2 message testing and development:

- **`funny_hl7_sender.py`** - Primary HL7 message sender supporting ADT and ORU message types via TCP/MLLP
- **`hl7_test_listener.py`** - HL7 message receiver with automatic ACK response generation
- **`show_funny_hl7_messages.py`** - Message preview utility for development and debugging
- **`README.md`** - Detailed documentation for the HL7 toolkit

**Purpose**: Testing and development of HL7 medical messaging integration, featuring humorous test data for "Matt Knee-Slapper Jr." at the "Funny Farm Asylum."

### DICOM Tools (`DICOM/`)
- Medical imaging format utilities and processors

### Support Directories
- **`backup/`** - Dated backups of modified files (maintains ≤50 copies per file)
- **`MSEdge/`** - Microsoft Edge related utilities

## Database Schema

Currently no centralized database. Individual tools may use:
- SQLite databases (local file-based)
- MongoDB connections (external)
- File-based data storage

## Current Feature Status

✅ **Completed**:
- HL7 message generation and transmission
- SQL to MongoDB migration
- Bootable USB creation automation
- SSD market data scraping

🚧 **In Development**:
- Enhanced DICOM processing capabilities
- Expanded medical data format support

## Known Issues/Constraints

- HL7 tools currently support v2.2 specification only
- PowerShell scripts require Windows environment
- Some utilities have hardcoded paths requiring local configuration

## Recent Changes

### 2025-09-11
- **Added HL7 Tools**: Consolidated HL7 messaging utilities into dedicated `HL7/` subdirectory
- **Files Migrated**: `funny_hl7_sender.py`, `hl7_test_listener.py`, `show_funny_hl7_messages.py`, `README.md`
- **Backups Created**: Dated backups in `backup/` directory following backup retention policy
- **No Database Changes**: HL7 tools operate independently without persistent storage requirements

---

*Architecture document maintained as per development workflow requirements. Updated after major feature additions.*
