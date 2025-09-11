# DICOM Transfer Syntax Fixer (ts fix)

This toolset helps detect, repair, and validate DICOM Transfer Syntax UIDs. It contains:
- transfer_syntax_fixer.py — a heuristic fixer that scans a directory, detects the most likely Transfer Syntax for each DICOM, and updates file meta accordingly.
- run_rubomedical_test.py — a harness that downloads public RuboMedical DICOM archives, clears Transfer Syntax in a working copy, runs the fixer, and produces HTML/Markdown/JSON reports.

## Features
- Detects common compressed and uncompressed syntaxes: Implicit/Explicit VR (LE/BE), JPEG Baseline/Extended/2000, RLE, etc.
- Uses file-header heuristics when Transfer Syntax is missing or invalid.
- Safe, in-place updates to each file’s meta header (write_like_original=False).
- Clear, per-file logs and aggregated statistics.
- Optional dry-run mode.

## Requirements
- Python 3.8+
- pydicom

Install:
```bash
python3 -m pip install pydicom
```

## Usage — Fixer
Run against a directory of DICOM files:
```bash
python3 transfer_syntax_fixer.py .
```

Useful flags:
- --dry-run — analyze without modifying files
- -v / --verbose — debug-level logging

Examples:
```bash
# Current directory
python3 transfer_syntax_fixer.py .

# Another directory
python3 transfer_syntax_fixer.py /path/to/dicom

# Preview only, verbose
python3 transfer_syntax_fixer.py . --dry-run --verbose
```

## Usage — RuboMedical Test Harness
run_rubomedical_test.py downloads a few public DICOM archives, prepares a working copy (with Transfer Syntax cleared), runs the fixer against the working copy, then reports.

Important: The script’s default --fixer path may reference an old location. Point it at this directory’s fixer explicitly:
```bash
python3 run_rubomedical_test.py \
  --limit 3 \
  --fixer "$(pwd)/transfer_syntax_fixer.py" \
  --report-dir "$HOME/.cache/rubo_dicom_report"
```

Outputs in report-dir:
- rubomedical_report.html — HTML view of the Markdown summary
- rubomedical_report.md — human-readable summary
- rubomedical_results.json — structured results

## Repo Layout (local)
```text
DICOM/transfer_syntax_fixer/
├─ transfer_syntax_fixer.py         # main fixer
├─ run_rubomedical_test.py          # test harness
├─ rubomedical_report.html          # sample report
├─ rubomedical_report.md            # sample report
└─ rubomedical_results.json         # sample report
```

## Notes & Limitations
- Heuristics are conservative; ambiguous cases fall back to common defaults (e.g., Implicit VR Little Endian).
- JPEG-family detection checks for common markers; edge cases may require manual review.
- Always keep backups of original data. This repo maintains a top-level backup/ directory for dated snapshots of code changes; for datasets, use your preferred archival process.

## Security & Privacy
Do not commit PHI or sensitive DICOM data. Use anonymized or public sample sets for testing.

## License
MIT (or repository default).

