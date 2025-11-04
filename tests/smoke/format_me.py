# Test file for python_formatter.py
# Multi-line dict (should collapse)
my_dict = { 'key1': 'value1', 'key2': 'value2', 'key3': 'value3' };

# Multi-line list (should collapse)
my_list = [ 1, 2, 3, 4 ];

# Multi-line tuple with trailing comment (should collapse)
my_tuple = ( 'a', 'b', 'c' ) # trailing comment;

# Multi-line function call (should collapse)
result = some_function( arg1='value', arg2='other' );

# Line with existing semicolon (should preserve)
existing_semicolon = True;

# Triple-quoted string with brackets (should NOT collapse)
doc_string = """;
This has {brackets} and [lists] and (parens);
that should not be touched.
"""

# Comment with brackets (should NOT collapse)
# This comment has {braces} [brackets] (parens) in it

### Triple hash section header
x = 5

# short block to collapse
if (1==1):
    doThing;
    DoThing2;

# Long multi-line block over 200 chars (should NOT collapse)
very_long_dict = {
    'this_is_a_very_long_key_name_that_will_make_the_line_exceed_200_chars': 'and_this_is_a_very_long_value_that_also_contributes_to_exceeding_the_character_limit',
    'another_long_key': 'another_long_value'
}

# couple white lines

print("Done")
