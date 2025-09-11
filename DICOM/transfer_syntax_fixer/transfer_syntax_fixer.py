#!/usr/bin/env python3
"""
DICOM Transfer Syntax Detection and Fixing Tool

This script recursively searches for DICOM files and:
1. Checks for existing Transfer Syntax UID (0002,0010) tag
2. If missing/invalid, uses heuristics to determine the correct transfer syntax
3. Updates the file with the correct transfer syntax if needed

Usage:
    python dicom_transfer_syntax_fixer.py [path]
    python dicom_transfer_syntax_fixer.py .  # Current directory
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import struct

try:
    import pydicom
    from pydicom import dcmread, dcmwrite
    from pydicom.dataset import Dataset, FileDataset
    from pydicom.tag import Tag
    from pydicom.uid import UID
except ImportError:
    print("Error: pydicom is required. Install with: pip install pydicom")
    sys.exit(1)

# Common transfer syntax UIDs
COMMON_TRANSFER_SYNTAXES = {
    '1.2.840.10008.1.2',           # Implicit VR Little Endian
    '1.2.840.10008.1.2.1',         # Explicit VR Little Endian
    '1.2.840.10008.1.2.2',         # Explicit VR Big Endian
    '1.2.840.10008.1.2.4.50',      # JPEG Baseline (Process 1)
    '1.2.840.10008.1.2.4.51',      # JPEG Extended (Process 2 & 4)
    '1.2.840.10008.1.2.4.70',      # JPEG Lossless (Process 14)
    '1.2.840.10008.1.2.4.80',      # JPEG-LS Lossless
    '1.2.840.10008.1.2.4.81',      # JPEG-LS Lossy
    '1.2.840.10008.1.2.4.90',      # JPEG 2000 Image Compression (Lossless Only)
    '1.2.840.10008.1.2.4.91',      # JPEG 2000 Image Compression
    '1.2.840.10008.1.2.4.92',      # JPEG 2000 Part 2 Multi-component Image Compression (Lossless Only)
    '1.2.840.10008.1.2.4.93',      # JPEG 2000 Part 2 Multi-component Image Compression
    '1.2.840.10008.1.2.5',         # RLE Lossless
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DICOMTransferSyntaxDetector:
    """Detects DICOM transfer syntax using various heuristics."""
    
    def __init__(self):
        self.stats = {
            'files_processed': 0,
            'files_updated': 0,
            'errors': 0,
            'transfer_syntaxes_found': {}
        }
    
    def is_dicom_file(self, filepath: Path) -> bool:
        """Check if file is a DICOM file by examining the header."""
        try:
            with open(filepath, 'rb') as f:
                # Check for DICOM preamble and prefix
                f.seek(128)  # Skip 128-byte preamble
                prefix = f.read(4)
                return prefix == b'DICM'
        except (IOError, OSError):
            return False
    
    def find_dicom_files(self, root_path: Path) -> List[Path]:
        """Recursively find all DICOM files in the given path."""
        dicom_files = []
        
        for file_path in root_path.rglob('*'):
            if file_path.is_file() and self.is_dicom_file(file_path):
                dicom_files.append(file_path)
        
        return dicom_files
    
    def get_current_transfer_syntax(self, dataset: FileDataset) -> Optional[str]:
        """Get the current transfer syntax UID from the dataset."""
        try:
            if hasattr(dataset, 'file_meta') and dataset.file_meta:
                ts_uid = dataset.file_meta.get('TransferSyntaxUID')
                if ts_uid:
                    return str(ts_uid)
        except Exception as e:
            logger.debug(f"Error getting transfer syntax: {e}")
        return None
    
    def detect_transfer_syntax_from_data(self, filepath: Path) -> str:
        """Detect transfer syntax using heuristics on the raw data."""
        try:
            with open(filepath, 'rb') as f:
                # Skip preamble and DICM prefix
                f.seek(132)
                
                # Read first few data elements to determine VR and endianness
                data = f.read(64)  # Read enough to analyze structure
                
                if len(data) < 8:
                    return '1.2.840.10008.1.2'  # Default to Implicit VR Little Endian
                
                # Check for explicit VR by looking for ASCII characters after tag
                tag_bytes = data[:4]
                vr_bytes = data[4:6]
                
                # Check if VR bytes are ASCII characters (explicit VR)
                if all(32 <= b <= 126 for b in vr_bytes):
                    # Check endianness by examining tag values
                    group, element = struct.unpack('<HH', tag_bytes)
                    if group == 0x0008 and element == 0x0005:  # Character Set tag
                        return '1.2.840.10008.1.2.1'  # Explicit VR Little Endian
                    else:
                        # Try big endian
                        group, element = struct.unpack('>HH', tag_bytes)
                        if group == 0x0008 and element == 0x0005:
                            return '1.2.840.10008.1.2.2'  # Explicit VR Big Endian
                        else:
                            return '1.2.840.10008.1.2.1'  # Default to Explicit VR Little Endian
                else:
                    # Implicit VR - check endianness
                    group, element = struct.unpack('<HH', tag_bytes)
                    if group == 0x0008 and element == 0x0005:
                        return '1.2.840.10008.1.2'  # Implicit VR Little Endian
                    else:
                        # Try big endian
                        group, element = struct.unpack('>HH', tag_bytes)
                        if group == 0x0008 and element == 0x0005:
                            return '1.2.840.10008.1.2.2'  # Implicit VR Big Endian
                        else:
                            return '1.2.840.10008.1.2'  # Default to Implicit VR Little Endian
                
        except Exception as e:
            logger.debug(f"Error detecting transfer syntax from data: {e}")
            return '1.2.840.10008.1.2'  # Default fallback
    
    def detect_compressed_transfer_syntax(self, filepath: Path) -> Optional[str]:
        """Detect compressed transfer syntax by examining pixel data."""
        try:
            with open(filepath, 'rb') as f:
                # Search for pixel data element (7FE0,0010)
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    
                    # Look for JPEG markers
                    if b'\xFF\xD8' in chunk:  # JPEG start marker
                        # Look for specific JPEG variants
                        f.seek(f.tell() - len(chunk))
                        data = f.read(2048)
                        
                        if b'\xFF\xC0' in data:  # JPEG baseline
                            return '1.2.840.10008.1.2.4.50'
                        elif b'\xFF\xC1' in data:  # JPEG extended
                            return '1.2.840.10008.1.2.4.51'
                        elif b'\xFF\xC2' in data:  # JPEG progressive
                            return '1.2.840.10008.1.2.4.51'
                        else:
                            return '1.2.840.10008.1.2.4.50'  # Default JPEG
                    
                    # Look for JPEG 2000 markers
                    if b'\x00\x00\x00\x0C\x6A\x50\x20\x20' in chunk:
                        return '1.2.840.10008.1.2.4.90'  # JPEG 2000 Lossless
                    elif b'\xFF\x4F\xFF\x51' in chunk:
                        return '1.2.840.10008.1.2.4.91'  # JPEG 2000
                    
                    # Look for RLE compression
                    if b'\xFE\xFE\x00\x00' in chunk:
                        return '1.2.840.10008.1.2.5'  # RLE Lossless
                
        except Exception as e:
            logger.debug(f"Error detecting compressed transfer syntax: {e}")
        
        return None
    
    def determine_transfer_syntax(self, filepath: Path) -> str:
        """Determine the correct transfer syntax using multiple heuristics."""
        # First, try to detect compressed transfer syntax
        compressed_ts = self.detect_compressed_transfer_syntax(filepath)
        if compressed_ts:
            return compressed_ts
        
        # If not compressed, detect from data structure
        return self.detect_transfer_syntax_from_data(filepath)
    
    def update_transfer_syntax(self, filepath: Path, new_transfer_syntax: str) -> bool:
        """Update the DICOM file with the correct transfer syntax."""
        try:
            # Read the file
            dataset = dcmread(filepath, force=True)
            
            # Ensure file_meta exists
            if not hasattr(dataset, 'file_meta') or not dataset.file_meta:
                dataset.file_meta = Dataset()
            
            # Update transfer syntax
            dataset.file_meta.TransferSyntaxUID = UID(new_transfer_syntax)
            
            # Write back to file
            dcmwrite(filepath, dataset, write_like_original=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating transfer syntax for {filepath}: {e}")
            return False
    
    def process_file(self, filepath: Path, dry_run: bool = False) -> Tuple[bool, str, str]:
        """Process a single DICOM file."""
        try:
            self.stats['files_processed'] += 1
            
            # Read the file
            dataset = dcmread(filepath, force=True)
            
            # Get current transfer syntax
            current_ts = self.get_current_transfer_syntax(dataset)
            
            # Check if current transfer syntax is valid
            if current_ts and current_ts in COMMON_TRANSFER_SYNTAXES:
                logger.info(f"✓ {filepath}: Valid transfer syntax {current_ts}")
                self.stats['transfer_syntaxes_found'][current_ts] = \
                    self.stats['transfer_syntaxes_found'].get(current_ts, 0) + 1
                return True, current_ts, current_ts
            
            # Determine correct transfer syntax
            logger.info(f"🔍 {filepath}: Detecting transfer syntax...")
            detected_ts = self.determine_transfer_syntax(filepath)
            
            logger.info(f"📋 {filepath}: Current: {current_ts or 'Missing'}, Detected: {detected_ts}")
            
            if not dry_run:
                # Update the file
                if self.update_transfer_syntax(filepath, detected_ts):
                    logger.info(f"✅ {filepath}: Updated to {detected_ts}")
                    self.stats['files_updated'] += 1
                    self.stats['transfer_syntaxes_found'][detected_ts] = \
                        self.stats['transfer_syntaxes_found'].get(detected_ts, 0) + 1
                    return True, current_ts or 'Missing', detected_ts
                else:
                    logger.error(f"❌ {filepath}: Failed to update")
                    self.stats['errors'] += 1
                    return False, current_ts or 'Missing', detected_ts
            else:
                logger.info(f"🔍 {filepath}: Would update to {detected_ts} (dry run)")
                self.stats['transfer_syntaxes_found'][detected_ts] = \
                    self.stats['transfer_syntaxes_found'].get(detected_ts, 0) + 1
                return True, current_ts or 'Missing', detected_ts
                
        except Exception as e:
            logger.error(f"❌ {filepath}: Error processing file - {e}")
            self.stats['errors'] += 1
            return False, 'Error', 'Error'
    
    def print_statistics(self):
        """Print processing statistics."""
        print("\n" + "="*60)
        print("PROCESSING STATISTICS")
        print("="*60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Files updated: {self.stats['files_updated']}")
        print(f"Errors: {self.stats['errors']}")
        print("\nTransfer syntaxes found:")
        for ts, count in sorted(self.stats['transfer_syntaxes_found'].items()):
            print(f"  {ts}: {count} files")
        print("="*60)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="DICOM Transfer Syntax Detection and Fixing Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dicom_transfer_syntax_fixer.py .                    # Process current directory
  python dicom_transfer_syntax_fixer.py /path/to/dicom/files # Process specific directory
  python dicom_transfer_syntax_fixer.py . --dry-run          # Preview changes without modifying files
  python dicom_transfer_syntax_fixer.py . --verbose          # Enable verbose logging
        """
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to search for DICOM files (default: current directory)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without modifying files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Convert path to Path object
    root_path = Path(args.path).resolve()
    
    if not root_path.exists():
        logger.error(f"Path does not exist: {root_path}")
        sys.exit(1)
    
    if not root_path.is_dir():
        logger.error(f"Path is not a directory: {root_path}")
        sys.exit(1)
    
    # Create detector instance
    detector = DICOMTransferSyntaxDetector()
    
    # Find DICOM files
    logger.info(f"Searching for DICOM files in: {root_path}")
    dicom_files = detector.find_dicom_files(root_path)
    
    if not dicom_files:
        logger.warning("No DICOM files found in the specified path")
        sys.exit(0)
    
    logger.info(f"Found {len(dicom_files)} DICOM files")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")
    
    # Process each file
    for filepath in dicom_files:
        detector.process_file(filepath, dry_run=args.dry_run)
    
    # Print statistics
    detector.print_statistics()


if __name__ == '__main__':
    main()
