#!/usr/bin/env python3
"""Custom Python formatter that adds semicolons to every line of code."""
import sys;
import re;

def check_indentation( lines ):
    """Check if indentation is correct for block levels and return warnings."""
    warnings = [];
    indent_stack = [ 0 ];
    
    for line_num, line in enumerate( lines, 1 ):
        stripped = line.lstrip();
        if not stripped or stripped.startswith( '#' ):
            continue;
        
        # Calculate current indentation (spaces or tabs)
        indent = len( line ) - len( stripped );
        
        # Check if previous line ended with colon (new block)
        if line_num > 1:
            prev_stripped = lines[ line_num - 2 ].rstrip();
            if prev_stripped.endswith( ':' ) or prev_stripped.endswith( ':;' ):
                expected_indent = indent_stack[ -1 ] + 4;
                if indent != expected_indent:
                    warnings.append( f"Line {line_num}: Expected indentation {expected_indent}, got {indent}" );
                if indent > indent_stack[ -1 ]:
                    indent_stack.append( indent );
            elif indent < indent_stack[ -1 ]:
                # Dedent
                while indent_stack and indent < indent_stack[ -1 ]:
                    indent_stack.pop();
                if indent_stack and indent != indent_stack[ -1 ]:
                    warnings.append( f"Line {line_num}: Indentation {indent} does not match any outer block level" );
    
    return warnings;

def add_semicolons( code ):
    """Add semicolons to every line of Python code (excluding blank lines, comments, and docstrings)."""
    lines = code.split( '\n' );
    result = [];
    in_multiline_comment = False;
    multiline_quote = None;

    for line in lines:
        stripped = line.rstrip();
        lstripped = stripped.lstrip();

        # Skip empty lines
        if not stripped:
            result.append( line );
            continue;

        # Check for multi-line comment start/end (""" or ''')
        if not in_multiline_comment:
            if lstripped.startswith( '"""' ) or lstripped.startswith( "'''" ):
                multiline_quote = lstripped[:3];
                in_multiline_comment = True;
                result.append( line );
                # Check if it ends on the same line
                if stripped.count( multiline_quote ) >= 2:
                    in_multiline_comment = False;
                continue;
        else:
            result.append( line );
            if multiline_quote in stripped:
                in_multiline_comment = False;
            continue;

        # Skip single-line comments
        if lstripped.startswith( '#' ):
            result.append( line );
            continue;

        # Remove :; pattern if it exists at the end
        if stripped.endswith( ':;' ):
            stripped = stripped[:-1];

        # If line already ends with punctuation, keep it
        if stripped.endswith( ( ';', ':', ',', '.', ')', ']', '}', '\\', '{' ) ):
            result.append( stripped );
            continue;

        # Add semicolon to code lines
        result.append( stripped + ';' );

    return '\n'.join( result );

if __name__ == '__main__':
    code = sys.stdin.read();
    
    # Check indentation and show warnings
    warnings = check_indentation( code.split( '\n' ) );
    if warnings:
        for warning in warnings:
            print( f"⚠️  {warning}", file=sys.stderr );
    
    formatted = add_semicolons( code );
    sys.stdout.write( formatted );
