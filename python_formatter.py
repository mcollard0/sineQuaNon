#!/usr/bin/env python3
"""
Custom Python formatter using the `tokenize` module.
Enforces:
1. Spaces inside brackets/parens: [ 1, 2 ], func( a )
2. Semicolons at end of statements (excluding pass, raise, block starters)
Safe for strings, comments, and f-strings.
"""
import sys
import argparse
import tokenize
import io
import token
import re

# Keywords that should NOT have a semicolon even if they end a line (directives)
DIRECTIVE_KEYWORDS = {
    'pass', 'raise', 'return', 'yield', 'break', 'continue'
}

def format_tokens(tokens):
    """
    Reconstructs code from tokens with applied formatting rules.
    """
    out = []
    last_lineno = -1
    last_col = 0
    
    # Filter out ENCODING
    tokens = [t for t in tokens if t.type != token.ENCODING]

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        type_ = tok.type
        string_ = tok.string
        start = tok.start
        end = tok.end
        line = tok.line
        
        # 1. WHITESPACE PRESERVATION/RECONSTRUCTION
        pad = ''
        if start[0] == last_lineno:
            current_col = start[1]
            if current_col > last_col:
                pad = ' ' * (current_col - last_col)
        elif start[0] > last_lineno:
             pad = ' ' * start[1]

        # 2. SPACE INSIDE BRACKETS RULES
        if i > 0:
            prev = tokens[i-1]
            if prev.type == token.OP and prev.string in '([{':
                is_empty = (prev.string == '(' and string_ == ')') or \
                           (prev.string == '[' and string_ == ']') or \
                           (prev.string == '{' and string_ == '}')
                if not is_empty and not pad and start[0] == last_lineno:
                       pad = ' '
            
            if type_ == token.OP and string_ in ')]}':
                is_empty = (prev.string == '(' and string_ == ')') or \
                           (prev.string == '[' and string_ == ']') or \
                           (prev.string == '{' and string_ == '}')
                if not is_empty and not pad and start[0] == last_lineno:
                        pad = ' '

        out.append(pad)
        
        # 2.5 F-STRING CLEANUP (F541)
        if type_ == token.STRING:
            # Check if it has f-prefix
            match = re.match(r'^([fFrR]+)([\'"].*)', string_, re.DOTALL)
            if match:
                prefix = match.group(1)
                rest = match.group(2)
                if 'f' in prefix.lower():
                    # It is an f-string. Check for placeholders (braces)
                    # Use 'rest' to avoid matching braces in prefix/quotes (though unlikely)
                    if '{' not in rest and '}' not in rest:
                        # Check for suppression
                        if not ("noqa" in line and "F541" in line):
                           # Remove f/F from prefix
                           new_prefix = prefix.replace('f', '').replace('F', '')
                           string_ = new_prefix + rest

        out.append(string_)
        
        # 3. SEMICOLON INSERTION LOGIC
        should_add_semi = False
        
        # Look ahead for "End of Statement" signals
        j = i + 1
        next_tok = None
        comment_found = False
        
        while j < len(tokens):
             t = tokens[j]
             if t.type == token.COMMENT:
                 comment_found = True
                 # We need to see what's AFTER the comment to decide
                 # If after comment is NL -> Continuation (no semi)
                 # If after comment is NEWLINE -> End of Stmt (semi)
                 k = j + 1
                 if k < len(tokens):
                     after_comment = tokens[k]
                     if after_comment.type == token.NEWLINE:
                         next_tok = t # Treat comment as end of stmt marker effectively
                         should_add_semi = True
                     elif after_comment.type == token.NL:
                         should_add_semi = False # Continuation
                         next_tok = t # Found something
                 break
             
             if t.type not in (token.NL, token.INDENT, token.DEDENT): 
                 next_tok = t
                 break
             j += 1
        
        if not comment_found:
            if next_tok:
                if next_tok.type in (token.NEWLINE, token.ENDMARKER):
                     should_add_semi = True
            else:
                if type_ != token.ENDMARKER:
                    should_add_semi = True
        
        # Exceptions logic modifies the 'should_add_semi' decision
        if should_add_semi:
            # 1. Current token is ':', ';', '\', ','
            if string_ in (':', ';', '\\', ','):
                should_add_semi = False
            
            # 2. Current token is INDENT/DEDENT/NEWLINE/NL/COMMENT/ENDMARKER
            if type_ in (token.INDENT, token.DEDENT, token.NEWLINE, token.NL, token.COMMENT, token.ENDMARKER):
                should_add_semi = False
            
            # 3. Directive and Decorator exclusion
            k = i
            while k >= 0:
                if tokens[k].type in (token.NEWLINE, token.INDENT, token.DEDENT):
                    break
                k -= 1
            start_idx = k + 1
            
            idx_scan = start_idx
            first_sig_token = None
            while idx_scan <= i:
                t = tokens[idx_scan]
                if t.type not in (token.NL, token.COMMENT):
                    first_sig_token = t
                    break
                idx_scan += 1
            
            if first_sig_token:
                 if first_sig_token.type == token.NAME and first_sig_token.string in DIRECTIVE_KEYWORDS:
                     should_add_semi = False
                 elif first_sig_token.type == token.OP and first_sig_token.string == '@':
                     should_add_semi = False

        if should_add_semi:
             out.append(';')
        
        last_lineno = end[0]
        last_col = end[1]
        
        i += 1

    return "".join(out)

def process_file(filepath, in_place):
    try:
        content = ""
        if filepath == '-':
            content = sys.stdin.read()
        else:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

        b_content = content.encode('utf-8')
        bio = io.BytesIO(b_content)
        
        try:
             tokens = list(tokenize.tokenize(bio.readline))
        except tokenize.TokenError as e:
             sys.stderr.write(f"⚠️  Tokenization error in {filepath}: {e}\n")
             return

        formatted = format_tokens(tokens)
        
        if in_place and filepath != '-':
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted)
        else:
            print(formatted)
            
    except Exception as e:
        sys.stderr.write(f"Error processing {filepath}: {e}\n")
        sys.exit(1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='*', help='Files to format')
    parser.add_argument('--in-place', '-i', action='store_true')
    args = parser.parse_args()
    
    if args.files:
        for f in args.files:
            process_file(f, args.in_place)
    else:
        process_file('-', False)
