# Warp Development Notes

## Python Cache Management

<!> **IMPORTANT:** When making changes to Python files, clear the bytecode cache to ensure changes take effect:

```bash
find /ARCHIVE/Programming/sineQuaNon -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find /ARCHIVE/Programming/sineQuaNon -type f -name "*.pyc" -delete 2>/dev/null
```

This is especially important when:
- Modifying `python_formatter.py`
- Testing changes in VS Code with the runonsave extension
- After updating any Python module

## Python Formatter

The custom Python formatter (`python_formatter.py`) is configured to run automatically in VS Code Insiders via the `emeraldwalk.runonsave` extension.

**To reload changes:**
1. Clear Python cache (see above)
2. Reload VS Code window: `Ctrl+Shift+P` → "Reload Window"

**Manual usage:**
```bash
python3 /ARCHIVE/Programming/sineQuaNon/python_formatter.py --in-place file.py
```

## Testing

Test files are located in `tests/smoke/` directory.
