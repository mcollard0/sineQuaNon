#!/usr/bin/env python3
"""Search all text columns in SQLite database for a query string."""

import sqlite3;
import sys;
import argparse;
from pathlib import Path;

def search_database( db_path: str, search_term: str, case_sensitive: bool = False ):
    """Search all text columns in all tables for the given term."""
    
    conn = sqlite3.connect( db_path );
    cursor = conn.cursor();
    
    # Get all tables
    cursor.execute( "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;" );
    tables = [ row[0] for row in cursor.fetchall() ];
    
    results = [];
    
    for table in tables:
        # Skip FTS and internal tables for performance
        if table.startswith( 'fts4_' ) or table.startswith( 'sqlite_' ) or table.startswith( 'spellfix_' ):
            continue;
            
        try:
            # Get column info for this table
            cursor.execute( f"PRAGMA table_info({table});" );
            columns = cursor.fetchall();
            
            # Filter to text-like columns (TEXT, VARCHAR, CHAR, etc.)
            text_columns = [
                col[1] for col in columns 
                if col[2].upper() in ( 'TEXT', 'VARCHAR', 'CHAR', 'CLOB', '' ) 
                or 'CHAR' in col[2].upper() 
                or 'TEXT' in col[2].upper()
            ];
            
            if not text_columns:
                continue;
            
            # Build WHERE clause for all text columns
            if case_sensitive:
                conditions = [ f"{col} LIKE '%{search_term}%'" for col in text_columns ];
            else:
                conditions = [ f"LOWER({col}) LIKE LOWER('%{search_term}%')" for col in text_columns ];
            where_clause = ' OR '.join( conditions );
            
            # Search this table
            query = f"SELECT * FROM {table} WHERE {where_clause};";
            cursor.execute( query );
            rows = cursor.fetchall();
            
            if rows:
                # Get column names for display
                col_names = [ col[1] for col in columns ];
                results.append( {
                    'table': table,
                    'columns': col_names,
                    'text_columns': text_columns,
                    'rows': rows
                } );
                print( f"\n{'='*80}" );
                print( f"TABLE: {table}" );
                print( f"Found {len(rows)} row(s)" );
                print( f"Text columns searched: {', '.join(text_columns)}" );
                print( f"{'='*80}" );
                
                for i, row in enumerate( rows, 1 ):
                    print( f"\n--- Row {i} ---" );
                    for col_name, value in zip( col_names, row ):
                        if value is not None and str( value ).strip():
                            # Highlight matching columns
                            value_str = str( value );
                            search_lower = search_term.lower();
                            value_lower = value_str.lower();
                            
                            is_match = ( search_lower in value_lower ) if not case_sensitive else ( search_term in value_str );
                            
                            if col_name in text_columns and is_match:
                                print( f"  >>> {col_name}: {value}" );
                            else:
                                print( f"  {col_name}: {value}" );
                                
        except sqlite3.Error as e:
            print( f"Error searching table {table}: {e}", file=sys.stderr );
            continue;
    
    conn.close();
    
    print( f"\n\n{'='*80}" );
    print( f"SUMMARY: Found matches in {len(results)} table(s)" );
    for result in results:
        print( f"  - {result['table']}: {len(result['rows'])} row(s)" );
    print( f"{'='*80}\n" );
    
    return results;

def main():
    parser = argparse.ArgumentParser(
        description='Search all text columns in SQLite database for a query string.'
    );
    
    parser.add_argument(
        'search_term',
        help='The text to search for in all text columns'
    );
    
    parser.add_argument(
        '--database',
        '-d',
        required=True,
        help='Path to SQLite database file'
    );
    
    parser.add_argument(
        '--case-sensitive',
        '-c',
        action='store_true',
        help='Perform case-sensitive search (default: case-insensitive)'
    );
    
    args = parser.parse_args();
    
    # Verify database exists
    db_path = Path( args.database );
    if not db_path.exists():
        print( f"Error: Database file not found: {args.database}", file=sys.stderr );
        sys.exit( 1 );
    
    print( f"Searching database for: '{args.search_term}'" );
    print( f"Database: {args.database}" );
    print( f"Case-sensitive: {args.case_sensitive}\n" );
    
    search_database( args.database, args.search_term, args.case_sensitive );

if __name__ == '__main__':
    main();
