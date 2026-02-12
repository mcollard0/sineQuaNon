#!/usr/bin/env python3
"""
GPU Memory Clearing Tool for GridShift

This utility safely clears GPU memory used by various applications, particularly
focusing on processes like the GridShift daemon that may have loaded AI models
(Whisper, etc.) in VRAM.

Features:
- Detects all available NVIDIA GPUs
- Shows current memory usage for each GPU
- Identifies processes using GPU memory
- Safely clears cached memory from PyTorch and TensorFlow
- Provides detailed feedback on memory cleared
- Supports multiple GPU scenarios
- Can selectively clear memory from specific processes

Usage:
    python clear_gpu_memory.py                    # Show GPU status
    python clear_gpu_memory.py --clear            # Clear all possible GPU memory
    python clear_gpu_memory.py --clear --force    # Force clear including system processes
    python clear_gpu_memory.py --pid 12345        # Clear memory from specific process
    python clear_gpu_memory.py --gpu 0            # Target specific GPU
"""

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import psutil
except ImportError:
    psutil = None

# Optional PyTorch import for memory clearing
try:
    import torch

    HAS_PYTORCH = True
except ImportError:
    HAS_PYTORCH = False
    torch = None

# Optional TensorFlow import for memory clearing
try:
    import tensorflow as tf

    HAS_TENSORFLOW = True
except ImportError:
    HAS_TENSORFLOW = False
    tf = None


class GPUMemoryManager:
    """Manages GPU memory clearing across different frameworks and processes"""

Examples:
  %(prog)s                          # Show GPU status
  %(prog)s --clear                  # Clear all GPU memory caches
  %(prog)s --clear --force          # Force clear including dangerous processes
  %(prog)s --pid 12345              # Kill specific process using GPU
  %(prog)s --gpu 0 --clear          # Target specific GPU (future enhancement)
  %(prog)s --json                   # Output in JSON format
        """,
    )

    parser.add_argument("--clear", "-c", action="store_true", help="Clear GPU memory caches")
    parser.add_argument("--force", "-f", action="store_true", help="Force operations (use with caution)")
    parser.add_argument("--pid", type=int, help="Kill specific process by PID")
    parser.add_argument("--gpu", type=int, help="Target specific GPU by index")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Setup logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create GPU memory manager
    gpu_manager = GPUMemoryManager()

    try:
        if args.json:
            # JSON output mode
            results = {}

            if args.clear:
                results = gpu_manager.clear_all_memory(force=args.force)
            elif args.pid:
                results = gpu_manager.kill_process(args.pid, force=args.force)
            else:
                results = {
                    "gpus": gpu_manager.get_gpu_info(),
                    "processes": gpu_manager.get_gpu_processes(),
                    "frameworks": {"pytorch_available": HAS_PYTORCH, "tensorflow_available": HAS_TENSORFLOW},
                }

            print(json.dumps(results, indent=2))

        else:
            # Normal output mode
            if args.clear:
                gpu_manager.clear_all_memory(force=args.force)
            elif args.pid:
                result = gpu_manager.kill_process(args.pid, force=args.force)
                if result["success"]:
                    gpu_manager.logger.info(f"✅ Process {args.pid} terminated successfully")
                else:
                    gpu_manager.logger.error(f"❌ Failed to terminate process {args.pid}: {result['error']}")
            else:
                gpu_manager.display_gpu_status()

    except KeyboardInterrupt:
        gpu_manager.logger.info("\n🛑 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        gpu_manager.logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
