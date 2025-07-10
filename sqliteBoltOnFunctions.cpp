/* Created by Michael Collard (yes, I know) at 12:46.
* 
* This function was to test if you could add on regex functions to sqlite3, natively. This prevents the round trip of copying the data to C++ and back, although that's exactly what it does. 
* 
* Your mileage may vary. 
* 
* Untested. 
*  
* 
* Documented functions:
   std::regex::flag_type parse_flags( const char* flags, std::string& pattern, bool& invalid_flag );
   static void regexp_func( sqlite3_context* context, int argc, sqlite3_value** argv );
   static void regex_replace_func( sqlite3_context* context, int argc, sqlite3_value** argv );
   void registerSqlLiteBoltOnFunctions(sqlite3 * db);
   int sqlLiteBoltOnRegexReplaceTest();

*/

#include <iostream>
#include <regex>
#include <sqlite3.h>
#include <string>
#include "sqliteBoltOnFunctions.h"

std::regex::flag_type parse_flags( const char* flags, std::string& pattern, bool& invalid_flag ) {
  std::regex::flag_type mode = std::regex::ECMAScript;
  invalid_flag               = false;
  if ( !flags ) {
    return mode;
  }
  std::string f( flags );
  for ( char c : f ) {
    switch ( c ) {
      case 'i':
        mode |= std::regex::icase;
        break;
      case 'm':
        break;
      case 'g':
        break;
      case 's':
        std::cerr << "Warning: 's' flag (dot matches newline) is not supported by std::regex.\n";
        break;
      case 'x': {
        std::string cleaned;
        bool        inClass = false, escaping = false;
        for ( size_t i = 0; i < pattern.length(); ++i ) {
          char c = pattern[ i ];
          if ( escaping ) {
            cleaned  += c;
            escaping  = false;
            continue;
          }
          if ( c == '\\' ) {
            cleaned  += c;
            escaping  = true;
            continue;
          }
          if ( c == '[' ) {
            inClass = true;
          }
          if ( c == ']' ) {
            inClass = false;
          }
          if ( !inClass && ( c == ' ' || c == '\t' || c == '\n' ) ) {
            continue;
          }
          if ( !inClass && c == '#' && ( i == 0 || pattern[ i - 1 ] == '\n' ) ) {
            while ( i < pattern.length() && pattern[ i ] != '\n' ) {
              i++;
            }
            continue;
          }
          cleaned += c;
        }
        pattern = cleaned;
        break;
      }
      default:
        invalid_flag = true;
        break;
    }
  }
  return mode;
}

static void regexp_func( sqlite3_context* context, int argc, sqlite3_value** argv ) {
  if ( argc < 2 || argc > 3 ) {
    sqlite3_result_error( context, "REGEXP requires 2 or 3 arguments", -1 );
    return;
  }
  const char* pattern = reinterpret_cast< const char* >( sqlite3_value_text( argv[ 0 ] ) );
  const char* value   = reinterpret_cast< const char* >( sqlite3_value_text( argv[ 1 ] ) );
  const char* flags   = ( argc == 3 ) ? reinterpret_cast< const char* >( sqlite3_value_text( argv[ 2 ] ) ) : nullptr;
  if ( !pattern || !value ) {
    sqlite3_result_int( context, 0 );
    return;
  }
  std::string           patternStr   = pattern;
  bool                  invalid_flag = false;
  std::regex::flag_type mode         = parse_flags( flags, patternStr, invalid_flag );
  if ( invalid_flag ) {
    sqlite3_result_error( context, "Invalid regex flag used", -1 );
    return;
  }
  try {
    std::regex re( patternStr, mode );
    sqlite3_result_int( context, std::regex_search( value, re ) ? 1 : 0 );
  } catch ( std::regex_error& ) { sqlite3_result_error( context, "Invalid regex", -1 ); }
}

static void regex_replace_func( sqlite3_context* context, int argc, sqlite3_value** argv ) {
  if ( argc < 3 || argc > 4 ) {
    sqlite3_result_error( context, "REGEX_REPLACE requires 3 or 4 arguments", -1 );
    return;
  }
  const char* src         = reinterpret_cast< const char* >( sqlite3_value_text( argv[ 0 ] ) );
  const char* pattern     = reinterpret_cast< const char* >( sqlite3_value_text( argv[ 1 ] ) );
  const char* replacement = reinterpret_cast< const char* >( sqlite3_value_text( argv[ 2 ] ) );
  const char* flags       = ( argc == 4 ) ? reinterpret_cast< const char* >( sqlite3_value_text( argv[ 3 ] ) ) : nullptr;
  if ( !src || !pattern || !replacement ) {
    sqlite3_result_null( context );
    return;
  }
  std::string           patternStr   = pattern;
  bool                  invalid_flag = false;
  std::regex::flag_type mode         = parse_flags( flags, patternStr, invalid_flag );
  if ( invalid_flag ) { sqlite3_result_error( context, "Invalid regex flag used", -1 ); return; }

  try {
    std::regex  re( patternStr, mode );
    std::string result = std::regex_replace( src, re, replacement );
    sqlite3_result_text( context, result.c_str(), -1, SQLITE_TRANSIENT );
  } catch ( std::regex_error& ) { sqlite3_result_error( context, "Invalid regex", -1 ); }
}

void registerSqlLiteBoltOnFunctions(sqlite3 * db) { // This function registers the custom SQL functions with SQLite
  sqlite3_create_function( db, "regexp", 3, SQLITE_UTF8 | SQLITE_DETERMINISTIC, nullptr, &regexp_func, nullptr, nullptr );
  sqlite3_create_function( db, "regex_replace", 4, SQLITE_UTF8 | SQLITE_DETERMINISTIC, nullptr, &regex_replace_func, nullptr, nullptr );
}

int sqlLiteBoltOnRegexReplaceTest() {
  sqlite3* db;
  if ( sqlite3_open( ":memory:", &db ) != SQLITE_OK ) { std::cerr << "Failed to open database\n"; return 1; }
  registerSqlLiteBoltOnFunctions( db );
  const char* setup = R"(
        CREATE TABLE test (val TEXT);
        INSERT INTO test (val) VALUES ('Apple pie'), ('banana'), ('Cherry Pepper');
    )";
  sqlite3_exec( db, setup, nullptr, nullptr, nullptr );

  const char*   query = "SELECT val, regex_replace(val, 'p+', 'P', 'i') FROM test;";
  sqlite3_stmt* stmt  = nullptr;
  if ( sqlite3_prepare_v2( db, query, -1, &stmt, nullptr ) == SQLITE_OK ) {
    std::cout << "Original | Replaced\n---------------------\n";
    while ( sqlite3_step( stmt ) == SQLITE_ROW ) {
      std::cout << sqlite3_column_text( stmt, 0 ) << " | " << sqlite3_column_text( stmt, 1 ) << "\n";
    }
    sqlite3_finalize( stmt );
  }

  sqlite3_close( db );
  return 0;
}
