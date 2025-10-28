/*
 * SQLite3 Levenshtein Distance Extension
 * 
 * Provides a fast C implementation of Levenshtein distance for SQLite3.
 * 
 * COMPILATION:
 *   gcc -shared -fPIC -o levenshtein.so sqlite_levenshtein.c -lsqlite3
 * 
 * USAGE IN SQLITE3:
 *   sqlite> .load ./levenshtein
 *   sqlite> SELECT levenshtein( 'kitten', 'sitting' );
 *   -- Returns: 3
 * 
 * USAGE IN PYTHON:
 *   import sqlite3
 *   conn = sqlite3.connect( 'your.db' );
 *   conn.enable_load_extension( True );
 *   conn.load_extension( './levenshtein' );
 *   cursor = conn.execute( "SELECT levenshtein( 'hello', 'hallo' )" );
 *   print( cursor.fetchone()[0] );  # Returns: 1
 */

#include <sqlite3ext.h>
SQLITE_EXTENSION_INIT1

#include <string.h>
#include <stdlib.h>

#define MIN3( a, b, c ) ( ( a ) < ( b ) ? ( ( a ) < ( c ) ? ( a ) : ( c ) ) : ( ( b ) < ( c ) ? ( b ) : ( c ) ) )

static void levenshtein_func( sqlite3_context *context, int argc, sqlite3_value **argv ) {
    const unsigned char *s1, *s2;
    int len1, len2;
    int *prev_row, *curr_row, *temp;
    int i, j;
    int result;

    if ( argc != 2 ) {
        sqlite3_result_error( context, "levenshtein() requires exactly 2 arguments", -1 );
        return;
    }

    if ( sqlite3_value_type( argv[0] ) == SQLITE_NULL || sqlite3_value_type( argv[1] ) == SQLITE_NULL ) {
        sqlite3_result_null( context );
        return;
    }

    s1 = sqlite3_value_text( argv[0] );
    s2 = sqlite3_value_text( argv[1] );
    
    if ( !s1 || !s2 ) {
        sqlite3_result_null( context );
        return;
    }

    len1 = strlen( ( const char * )s1 );
    len2 = strlen( ( const char * )s2 );

    if ( len1 == 0 ) {
        sqlite3_result_int( context, len2 );
        return;
    }
    if ( len2 == 0 ) {
        sqlite3_result_int( context, len1 );
        return;
    }

    prev_row = ( int * )malloc( ( len2 + 1 ) * sizeof( int ) );
    curr_row = ( int * )malloc( ( len2 + 1 ) * sizeof( int ) );

    if ( !prev_row || !curr_row ) {
        if ( prev_row ) free( prev_row );
        if ( curr_row ) free( curr_row );
        sqlite3_result_error_nomem( context );
        return;
    }

    for ( j = 0; j <= len2; j++ ) {
        prev_row[j] = j;
    }

    for ( i = 0; i < len1; i++ ) {
        curr_row[0] = i + 1;

        for ( j = 0; j < len2; j++ ) {
            int cost = ( s1[i] == s2[j] ) ? 0 : 1;
            curr_row[j + 1] = MIN3(
                prev_row[j + 1] + 1,      // deletion
                curr_row[j] + 1,          // insertion
                prev_row[j] + cost        // substitution
            );
        }

        temp = prev_row;
        prev_row = curr_row;
        curr_row = temp;
    }

    result = prev_row[len2];

    free( prev_row );
    free( curr_row );

    sqlite3_result_int( context, result );
}

#ifdef _WIN32
__declspec( dllexport )
#endif
int sqlite3_levenshtein_init( sqlite3 *db, char **pzErrMsg, const sqlite3_api_routines *pApi ) {
    SQLITE_EXTENSION_INIT2( pApi );
    
    return sqlite3_create_function(
        db,
        "levenshtein",
        2,
        SQLITE_UTF8 | SQLITE_DETERMINISTIC,
        NULL,
        levenshtein_func,
        NULL,
        NULL
    );
}

#ifdef _WIN32
__declspec( dllexport )
#endif
int sqlite3_extension_init( sqlite3 *db, char **pzErrMsg, const sqlite3_api_routines *pApi ) {
    return sqlite3_levenshtein_init( db, pzErrMsg, pApi );
}
