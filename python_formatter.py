#!/usr/bin/env python3
"""Custom Python formatter that adds semicolons and collapses short multi-line blocks."""
import sys;
import argparse;
import re;

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
            triple_quote_found = False;
            for quote in [ '"""', "'''" ]:
                if quote in stripped:
                    count = stripped.count( quote );
                    if count == 1:
                        # Opening triple quote
                        in_triple = quote;
                        result.append( line );
                        i += 1;
                        triple_quote_found = True;
                        break
                    elif count == 2:
                        # Triple quote opens and closes on same line
                        result.append( line );
                        i += 1;
                        triple_quote_found = True;
                        break
            if triple_quote_found:
                continue
        else:
            # Inside triple-quoted string
            result.append( line );
            if in_triple in line:
                # Closing triple quote found
                in_triple = None;
            i += 1;
            continue
        
        # Skip comments
        if stripped.startswith( '#' ):
            result.append( line );
            i += 1;
            continue
        
        # Check for opening brackets at end of line ( multi-line block start )
        open_brackets = { '(': ')', '[': ']', '{': '}' };
        found_open = None;
        open_pos = -1;
        
        for bracket in open_brackets:
            pos = line.rfind( bracket );
            if pos != -1 and pos > open_pos:
                # Check if bracket is in a string ( simple check )
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
            #indent = line[ :len( line ) - len( line.lstrip() ) ];
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
                    break
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
                        continue
                
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
    
    return '\n'.join( result )

def check_indentation( lines ):
    """Check if indentation is correct for block levels and return warnings."""
    warnings = [];
    indent_stack = [ 0 ];
    
    for line_num, line in enumerate( lines, 1 ):
        stripped = line.lstrip();
        if not stripped or stripped.startswith( '#' ):
            continue
        
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
    
    return warnings

def add_spaces_inside_brackets( code ):
    """Add single space after opening and before closing brackets/parens/braces.
    
    Uses regex to avoid modifying content inside strings.
    Example: [1,2] -> [ 1,2 ], print(x) -> print( x ), {a:b} -> { a:b }
    """
    
    # Split code into string and non-string segments
    # This regex matches strings (single, double, triple-quoted) and captures them
    # Order matters: check triple-quotes before single quotes
    string_pattern = r'(  """(?:[^"]|"(?!""))*"""|' + r"'''( ?:[ ^']|'( ?!'' ) )*'''" + r'|"(?:[^"\\ ]|\\. )*"|' + r"'(?:[^'\\ ]|\\. )*')";
    
    def add_spaces_to_segment( text ):
        """Add spaces to brackets in non-string text."""
        # Add space after opening brackets if not already present
        # (?<=[\(\[\{]) = lookbehind for opening bracket
        # (?!\s) = not followed by whitespace
        # (?![\)\]\}]) = not followed by closing bracket (empty brackets)
        text = re.sub( r'( ?<=[ \( \[ \{] )( ?!\s )( ?![ \ )\ ]\ } ] )', ' ', text );
        
        # Add space before closing brackets if not already present
        # (?<!\s) = not preceded by whitespace
        # (?<![\(\[\{]) = not preceded by opening bracket (empty brackets)
        # (?=[\)\]\}]) = lookahead for closing bracket
        text = re.sub( r'( ?<!\s )( ?<![ \( \[ \{] )( ?=[ \ )\ ]\ } ] )', ' ', text );
        
        return text
    
    # Process code: split by strings, add spaces only to non-string parts
    parts = re.split( string_pattern, code, flags=re.DOTALL );
    result = [];
    
    for i, part in enumerate( parts ):
        if part is None:
            continue
        # Odd indices are captured groups (strings), even indices are non-string code
        if i % 2 == 0:
            # Non-string code - add spaces
            result.append( add_spaces_to_segment( part ) );
        else:
            # String literal - preserve as-is
            result.append( part );
    
    return ''.join( result )

def collapse_blank_lines( code ):
    """Collapse multiple consecutive blank lines to maximum of one blank line.
    
    Preserves blank lines inside strings (triple-quoted), but collapses
    excessive blank lines in regular code.
    """
    lines = code.split( '\n' );
    result = [];
    in_triple = None;
    consecutive_blanks = 0;
    
    for line in lines:
        stripped = line.strip();
        
        # Track triple-quoted strings
        if not in_triple:
            # Check for triple quote start
            for quote in [ '"""', "'''" ]:
                if quote in stripped:
                    count = stripped.count( quote );
                    if count == 1:
                        # Opening triple quote
                        in_triple = quote;
                        result.append( line );
                        consecutive_blanks = 0;
                        break
                    elif count == 2:
                        # Triple quote opens and closes on same line
                        result.append( line );
                        consecutive_blanks = 0;
                        break
            else:
                # Not a triple quote line
                if not stripped:
                    # Blank line
                    consecutive_blanks += 1;
                    # Only keep first blank line
                    if consecutive_blanks == 1:
                        result.append( line );
                else:
                    # Non-blank line
                    consecutive_blanks = 0;
                    result.append( line );
        else:
            # Inside triple-quoted string - preserve everything
            result.append( line );
            if in_triple in line:
                # Closing triple quote found
                in_triple = None;
                consecutive_blanks = 0;
    
    return '\n'.join( result )

def remove_useless_fstrings( code ):
    """Remove f prefix from strings that don't contain placeholders {}."""
    # Match "..." or '...' strings and check if they contain {}
    import re;
    
    def replace_fstring( match ):
        quote_char = match.group( 1 ); # Single or double quote
        content = match.group( 2 ); # String content
        
        # Check if content has placeholders
        if '{ ' in content and ' }' in content:
            # Keep f-string
            return match.group( 0 )
        else:
            # Remove f prefix
            return f"{ quote_char }{ content }{ quote_char }"
    
    # Pattern to match "..." or '...' (handling escaped quotes)
    # Match f followed by quote, then content, then closing quote
    pattern = r'\bf( [ "\'])(((?!(?<!\\)\1).)*?)\1';
    
    result = re.sub( pattern, replace_fstring, code );
    return result

def add_semicolons( code ):
    """Add semicolons to every line of Python code ( excluding blank lines, comments, and docstrings )."""
    lines = code.split( '\n' );
    result = [];
    in_multiline_comment = False;
    multiline_quote = None;
    bracket_depth = 0; # Track if we're inside brackets

    for line_idx, line in enumerate( lines ):
        stripped = line.rstrip();
        lstripped = stripped.lstrip();
        
        # Count brackets on this line (simple count, not perfect but good enough)
        open_count = stripped.count( '( ' ) + stripped.count( '[ ' ) + stripped.count( '{ ' );
        close_count = stripped.count( ' )' ) + stripped.count( ' ]' ) + stripped.count( ' }' )
        
        # Skip empty lines
        if not stripped:
            result.append( line );
            continue

        # Check for multi-line comment start/end (""" or ''' )
        if not in_multiline_comment:
            if lstripped.startswith( '"""' ) or lstripped.startswith( "'''" ):
                multiline_quote = lstripped[ :3 ];
                in_multiline_comment = True;
                result.append( line );
                # Check if it ends on the same line
                if stripped.count( multiline_quote ) >= 2:
                    in_multiline_comment = False;
                continue
        else:
            result.append( line );
            if multiline_quote in stripped:
                in_multiline_comment = False;
            continue

        # Skip single-line comments
        if lstripped.startswith( '#' ):
            result.append( line );
            continue
        
        # Skip decorators ( lines starting with @ )
        if lstripped.startswith( '@' ):
            # Remove semicolon if it exists on decorator
            if stripped.endswith( ';' ):
                stripped = stripped[ :-1 ];
            result.append( stripped );
            continue

        # Remove :; pattern if it exists at the end
        if stripped.endswith( ':;' ):
            stripped = stripped[ :-1 ];

        # If line ends with opening bracket, update depth and don't add semicolon
        if stripped.endswith( ( '( ', '[ ', '{ ' ) ):
            bracket_depth += open_count - close_count
            result.append( stripped )
            continue
        
        # Remove semicolon if it appears right after opening bracket (syntax error)
        if '( ' in stripped or '[ ' in stripped or '{ ' in stripped:
            stripped = stripped.replace( '( ', '( ' ).replace( '[ ', '[ ' ).replace( '{ ', '{ ' )
        
        # Check if we're currently inside brackets BEFORE updating depth
        was_inside_brackets = bracket_depth > 0
        
        # Update bracket depth
        bracket_depth += open_count - close_count
        
        # If we were inside brackets or line ends with opening bracket, don't add semicolon
        if was_inside_brackets or stripped.endswith( ( '( ', '[ ', '{ ' ) ):
            # Remove trailing semicolon if it exists (shouldn't be there )
            if stripped.endswith( ';' ) and not stripped.endswith( ':;' ):
                stripped = stripped[ :-1 ]
            result.append( stripped )
            continue
        
        # Check if line has inline comment ( code followed by # )
        # Need to find # that's not inside a string
        # Match strings and find # outside of them
        in_string = False
        string_char = None
        comment_pos = -1
        
        for i, char in enumerate( stripped ):
            if not in_string:
                if char in [ '"', "'" ]:
                    # Check if not escaped
                    if i == 0 or stripped[i-1] != '\\':
                        in_string = True
                        string_char = char
                elif char == '#':
                    comment_pos = i
                    break
            else:
                if char == string_char:
                    # Check if not escaped
                    if i == 0 or stripped[i-1] != '\\':
                        in_string = False
                        string_char = None
        
        if comment_pos > 0:
            # Has inline comment - add semicolon before the comment unless it's a raise statement
            code_part = stripped[ :comment_pos ].rstrip()
            comment_part = stripped[ comment_pos: ]
            
            # Special case: never add semicolon to raise statements, even with comments
            if code_part.lstrip().startswith( 'raise' ):
                result.append( code_part + ' ' + comment_part )
                continue
            
            # Check if code part already ends with semicolon or other punctuation
            if code_part.endswith( ( ';', ':', ',', '.', '\\', ' or', ' and' ) ):
                result.append( stripped )
            else:
                result.append( code_part + '; ' + comment_part )
            continue
        
        # Check if line ends with control flow keywords that shouldn't have semicolons
        # These are statements that change flow: raise, return, break, continue, pass, yield
        control_keywords = [ 'raise', 'return', 'break', 'continue', 'pass', 'yield' ]
        ends_with_control = False
        for keyword in control_keywords:
            # Check if line ends with keyword (possibly followed by whitespace)
            if lstripped.startswith( keyword + ' ' ) or lstripped == keyword:
                # Make sure it's actually the keyword and not part of a larger identifier
                # Check the code part ( before any comment )
                code_only = stripped.split( '#' )[ 0 ].rstrip()
                if code_only.endswith( keyword ) or keyword + ' ' in code_only or keyword + '(' in code_only:
                    ends_with_control = True
                    break
        
        if ends_with_control:
            result.append( stripped )
            continue
        
        # If line already ends with certain punctuation or boolean operators, keep it
        # Note: ) ] } are NOT in this list because complete statements like print() should get semicolons
        if stripped.endswith( ( ';', ':', ',', '.', '\\', ' or', ' and' ) ):
            result.append( stripped )
            continue
        
        # Special case: if line ends with ) and next line is indented more, don't add semicolon
        # (This is a function/class definition followed by a block)
        if stripped.endswith( ' )' ):
            # Check if there's a next line
            if line_idx + 1 < len( lines ):
                next_line = lines[ line_idx + 1 ]
                # Get current and next line indentation
                current_indent = len( line ) - len( line.lstrip() )
                next_indent = len( next_line ) - len( next_line.lstrip() )
                # If next line is indented more ( and not empty/comment ), don't add semicolon
                next_stripped = next_line.strip()
                if next_stripped and not next_stripped.startswith( '#' ) and next_indent > current_indent:
                    result.append( stripped )
                    continue

        # Add semicolon to code lines
        result.append( stripped + ';' )

    return '\n'.join( result )

if __name__ == '__main__':
    parser = argparse.ArgumentParser( description='Custom Python formatter' )
    parser.add_argument( 'files', nargs='*', help='Files to format' )
    parser.add_argument( '--in-place', '-i', action='store_true', help='Format files in place' )
    args = parser.parse_args()
    
    if args.files:
        # Format files
        for filepath in args.files:
            try:
                with open( filepath, 'r' ) as f:
                    code = f.read()
            except Exception as e:
                print( f"Error reading { filepath }: { e }", file=sys.stderr )
                sys.exit( 1 )
            
            # Apply formatting pipeline
            formatted = remove_useless_fstrings( code )
            formatted = add_spaces_inside_brackets( formatted )
            formatted = add_semicolons( formatted )
            formatted = collapse_multiline_blocks( formatted )
            formatted = collapse_blank_lines( formatted )
            
            # Check indentation and show warnings
            warnings = check_indentation( formatted.split( '\n' ) )
            if warnings:
                for warning in warnings:
                    print( f"⚠️  { filepath }: { warning }", file=sys.stderr )
            
            if args.in_place:
                try:
                    with open( filepath, 'w' ) as f:
                        f.write( formatted )
                except Exception as e:
                    print( f"Error writing { filepath }: { e }", file=sys.stderr )
                    sys.exit( 1 )
            else:
                sys.stdout.write( formatted )
    else:
        # Read from stdin
        code = sys.stdin.read()
        
        # Apply formatting pipeline
        formatted = remove_useless_fstrings( code )
        formatted = add_spaces_inside_brackets( formatted )
        formatted = add_semicolons( formatted )
        formatted = collapse_multiline_blocks( formatted )
        formatted = collapse_blank_lines( formatted )
        
        # Check indentation and show warnings
        warnings = check_indentation( formatted.split( '\n' ) )
        if warnings:
            for warning in warnings:
                print( f"⚠️  { warning }", file=sys.stderr )
        
        sys.stdout.write( formatted )
