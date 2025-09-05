#!/usr/bin/env python3
"""
Simple SQL to MongoDB Query Runner

A lightweight wrapper that converts basic SQL to MongoDB and executes it.
Focuses on simplicity and reliability.

Usage:
    python3 sqlq.py "SELECT * FROM food_businesses WHERE business_type = 'Retail Bakeries'"
    python3 sqlq.py "SELECT business_name, address FROM food_businesses LIMIT 5"
"""

import sys
import os
import re
import json
import subprocess

def sql_to_mongo(sql_query, collection='food_businesses'):
    """Convert SQL to MongoDB query using regex patterns."""
    sql = sql_query.strip().rstrip(';')
    
    # SELECT queries
    select_match = re.match(
        r'SELECT\s+(.+?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$',
        sql, re.IGNORECASE | re.DOTALL
    )
    
    if select_match:
        fields, table, where, order_by, limit = select_match.groups()
        
        # Build find query
        query_parts = [f"db.{collection}.find("]
        
        # Where clause
        if where:
            filter_obj = {}
            # Simple equality: field = 'value'
            eq_matches = re.findall(r'(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]', where, re.IGNORECASE)
            for field, value in eq_matches:
                filter_obj[field] = value
            query_parts.append(json.dumps(filter_obj))
        else:
            query_parts.append("{}")
        
        # Fields projection
        if fields.strip() != '*':
            projection = {}
            for field in fields.split(','):
                field = field.strip()
                if field != '*':
                    projection[field] = 1
            query_parts.append(f", {json.dumps(projection)}")
        
        query_parts.append(")")
        
        # Order by
        if order_by:
            sort_obj = {}
            for sort_field in order_by.split(','):
                parts = sort_field.strip().split()
                field_name = parts[0]
                direction = 1 if len(parts) == 1 or parts[1].upper() == 'ASC' else -1
                sort_obj[field_name] = direction
            query_parts.append(f".sort({json.dumps(sort_obj)})")
        
        # Limit
        if limit:
            query_parts.append(f".limit({limit})")
            
        return ''.join(query_parts)
    
    return None

def execute_mongo_query(mongo_query, mongodb_uri, database='kansas_city'):
    """Execute MongoDB query and return results."""
    if not mongodb_uri:
        print("Error: mongodb_uri environment variable not set", file=sys.stderr)
        return False
    
    # Create a script that will format output nicely
    script = f"""
    use {database};
    cursor = {mongo_query};
    if (cursor && typeof cursor.forEach === 'function') {{
        cursor.forEach(function(doc) {{
            print(JSON.stringify(doc, null, 2));
        }});
    }} else {{
        printjson(cursor);
    }}
    """
    
    try:
        result = subprocess.run(
            ['mongosh', mongodb_uri, '--quiet', '--eval', script],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Filter out the "switched to db" message
            lines = result.stdout.split('\n')
            output_lines = [line for line in lines if not line.startswith('switched to db')]
            output = '\n'.join(output_lines).strip()
            if output:
                print(output)
            return True
        else:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return False
            
    except Exception as e:
        print(f"Error executing query: {e}", file=sys.stderr)
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 sqlq.py \"SQL_QUERY\"")
        print("\nExamples:")
        print("  python3 sqlq.py \"SELECT * FROM food_businesses LIMIT 5\"")
        print("  python3 sqlq.py \"SELECT business_name FROM food_businesses WHERE business_type = 'Retail Bakeries'\"")
        return 1
    
    sql_query = sys.argv[1]
    mongodb_uri = os.getenv('mongodb_uri', '')
    
    if not mongodb_uri:
        print("Error: mongodb_uri environment variable not set", file=sys.stderr)
        return 1
    
    mongo_query = sql_to_mongo(sql_query)
    if not mongo_query:
        print(f"Error: Could not convert SQL query: {sql_query}", file=sys.stderr)
        return 1
    
    print(f"MongoDB query: {mongo_query}", file=sys.stderr)
    success = execute_mongo_query(mongo_query, mongodb_uri)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
