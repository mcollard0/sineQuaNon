#!/usr/bin/env python3
"""Custom Python formatter that adds semicolons and collapses short multi-line blocks."""
import sys;
import re;
import argparse;

def collapse_multiline_blocks( code, max_len=200 ):
    """Collapse multi-line blocks to single lines if total length <= max_len."""
    lines = code.split( '\n' );
    result = [];
    i = 0;
    in_triple = None;
    
    while i < len( lines ):
        line = lines[ i ];
        stripped = line.lstrip();
        
        # Track triple-quoted strings
        if not in_triple:
            for quote in [ '"""', "'''" ]:
                if quote in stripped and stripped.count( quote ) == 1:
                    in_triple = quote;
                    break;
        elif in_triple and in_triple in line:
            in_triple = None;
            result.append( line );
            i += 1;
            continue;
        
        # Skip if in triple-quoted string
        if in_triple:
            result.append( line );
            i += 1;
            continue;
        
        # Skip comments
        if stripped.startswith( '#' ):
            result.append( line );
            i += 1;
            continue;
        
        # Check for opening brackets at end of line (multi-line block start)
        open_brackets = { '(': ')', '[': ']', '{': '}' };
        found_open = None;
        open_pos = -1;
        
        for bracket in open_brackets:
            pos = line.rfind( bracket );
            if pos != -1 and pos > open_pos:
                # Check if bracket is in a string (simple check)
                before = line[ :pos ];
                single_q = before.count( "'" ) - before.count( "\\'" );
                double_q = before.count( '"' ) - before.count( '\\"' );
                if single_q % 2 == 0 and double_q % 2 == 0:
                    # Check if not already closed on same line
                    after = line[ pos + 1: ];
                    if open_brackets[ bracket ] not in after:
                        found_open = bracket;
                        open_pos = pos;
        
        if found_open:
            # Multi-line block starting
            indent = line[ :len( line ) - len( line.lstrip() ) ];
            prefix = line[ :open_pos + 1 ];
            close_bracket = open_brackets[ found_open ];
            
            # Collect lines until closing bracket
            block_lines = [ line[ open_pos + 1: ] ];
            j = i + 1;
            found_close = False;
            
            while j < len( lines ):
                next_line = lines[ j ];
                block_lines.append( next_line );
                if close_bracket in next_line:
                    found_close = True;
                    break;
                j += 1;
            
            if found_close and j > i:
                # Extract closing line
                last_line = block_lines[ -1 ];
                close_pos = last_line.find( close_bracket );
                suffix = last_line[ close_pos + 1: ].strip();
                block_lines[ -1 ] = last_line[ :close_pos ];
                
                # Check for internal comments
                has_comment = any( '#' in bl for bl in block_lines[ :-1 ] );
                
                if not has_comment:
                    # Join content
                    content = ' '.join( bl.strip() for bl in block_lines ).strip();
                    collapsed = f"{prefix} {content} {close_bracket}";
                    if suffix:
                        collapsed += ' ' + suffix;
                    
                    # Check length
                    if len( collapsed ) <= max_len:
                        result.append( collapsed );
                        i = j + 1;
                        continue;
                
                # Can't collapse - add all original lines
                result.append( line );
                for k in range( i + 1, j + 1 ):
                    if k < len( lines ):
                        result.append( lines[ k ] );
                i = j + 1;
            else:
                result.append( line );
                i += 1;
        else:
            result.append( line );
            i += 1;
    
    return '\n'.join( result );

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
    parser = argparse.ArgumentParser( description='Custom Python formatter' );
    parser.add_argument( 'files', nargs='*', help='Files to format' );
    parser.add_argument( '--in-place', '-i', action='store_true', help='Format files in place' );
    args = parser.parse_args();
    
    if args.files:
        # Format files
        for filepath in args.files:
            try:
                with open( filepath, 'r' ) as f:
                    code = f.read();
            except Exception as e:
                print( f"Error reading {filepath}: {e}", file=sys.stderr );
                sys.exit( 1 );
            
            # Apply formatting pipeline
            code = collapse_multiline_blocks( code );
            formatted = add_semicolons( code );
            
            # Check indentation and show warnings
            warnings = check_indentation( formatted.split( '\n' ) );
            if warnings:
                for warning in warnings:
                    print( f"⚠️  {filepath}: {warning}", file=sys.stderr );
            
            if args.in_place:
                try:
                    with open( filepath, 'w' ) as f:
                        f.write( formatted );
                except Exception as e:
                    print( f"Error writing {filepath}: {e}", file=sys.stderr );
                    sys.exit( 1 );
            else:
                sys.stdout.write( formatted );
    else:
        # Read from stdin
        code = sys.stdin.read();
        
        # Apply formatting pipeline
        code = collapse_multiline_blocks( code );
        formatted = add_semicolons( code );
        
        # Check indentation and show warnings
        warnings = check_indentation( formatted.split( '\n' ) );
        if warnings:
            for warning in warnings:
                print( f"⚠️  {warning}", file=sys.stderr );
        
        sys.stdout.write( formatted );
