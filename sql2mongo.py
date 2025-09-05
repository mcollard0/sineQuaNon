#!/usr/bin/env python3
"""
SQL to MongoDB Query Converter

Converts SQL queries to MongoDB queries using AI or regex patterns.
Supports INSERT, UPDATE, DELETE, and SELECT operations.

Usage:
    python3 sql2mongo.py "SELECT * FROM food_businesses WHERE business_type = 'Retail Bakeries'"
    python3 sql2mongo.py "INSERT INTO food_businesses (business_name, address) VALUES ('Test', '123 Main St')"
    python3 sql2mongo.py "UPDATE food_businesses SET deleted = true WHERE business_name = 'Test'"
    python3 sql2mongo.py "DELETE FROM food_businesses WHERE business_name = 'Test'"

Environment Variables (in order of preference):
    ANTHROPIC_API_KEY - Anthropic Claude API
    OPENAI_API_KEY - OpenAI GPT API  
    GOOGLE_API_KEY or GEMINI_API_KEY - Google Gemini API
    XAI_API_KEY - xAI Grok API

If no AI API is available, falls back to regex-based conversion.
"""

import sys
import os
import re
import json
import subprocess
import argparse
from typing import Optional, Dict, Any, Tuple

# Standard environment variable names for AI APIs
AI_PROVIDERS = {
    'anthropic': ['ANTHROPIC_API_KEY'],
    'openai': ['OPENAI_API_KEY'],
    'gemini': ['GOOGLE_API_KEY', 'GEMINI_API_KEY'],
    'xai': ['XAI_API_KEY']
}

class SQLToMongoConverter:
    def __init__(self):
        self.mongodb_uri = os.getenv('mongodb_uri', '')
        self.database = os.getenv('MONGO_DB', 'kansas_city')
        self.collection = os.getenv('MONGO_COLLECTION', 'food_businesses')
        self.ai_provider = None
        self.ai_key = None
        self._detect_ai_provider()
    
    def _detect_ai_provider(self) -> None:
        """Detect which AI provider is available based on environment variables."""
        for provider, env_vars in AI_PROVIDERS.items():
            for env_var in env_vars:
                key = os.getenv(env_var)
                if key:
                    self.ai_provider = provider
                    self.ai_key = key
                    print(f"Using {provider.upper()} AI provider", file=sys.stderr)
                    return
        
        print("No AI provider found, using regex-based conversion", file=sys.stderr)
    
    def convert_with_ai(self, sql_query: str) -> Optional[str]:
        """Convert SQL to MongoDB using AI."""
        if not self.ai_provider or not self.ai_key:
            return None
            
        prompt = f"""Convert this SQL query to MongoDB shell format. Return only the MongoDB command(s), no explanation.

Database: {self.database}
Collection: {self.collection}

SQL Query: {sql_query}

Examples:
- SELECT * FROM table WHERE field = 'value' → db.collection.find({{field: 'value'}})
- INSERT INTO table (field1, field2) VALUES ('val1', 'val2') → db.collection.insertOne({{field1: 'val1', field2: 'val2'}})
- UPDATE table SET field = 'value' WHERE id = 1 → db.collection.updateMany({{id: 1}}, {{$set: {{field: 'value'}}}})
- DELETE FROM table WHERE field = 'value' → db.collection.deleteMany({{field: 'value'}})

MongoDB command:"""

        try:
            if self.ai_provider == 'anthropic':
                return self._anthropic_request(prompt)
            elif self.ai_provider == 'openai':
                return self._openai_request(prompt)
            elif self.ai_provider == 'gemini':
                return self._gemini_request(prompt)
            elif self.ai_provider == 'xai':
                return self._xai_request(prompt)
        except Exception as e:
            print(f"AI conversion failed: {e}", file=sys.stderr)
            return None
    
    def _anthropic_request(self, prompt: str) -> Optional[str]:
        """Make request to Anthropic Claude API."""
        try:
            import requests
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'Content-Type': 'application/json',
                    'X-API-Key': self.ai_key,
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-3-haiku-20240307',
                    'max_tokens': 1000,
                    'messages': [{'role': 'user', 'content': prompt}]
                }
            )
            if response.status_code == 200:
                return response.json()['content'][0]['text'].strip()
        except ImportError:
            print("requests library not available for AI conversion", file=sys.stderr)
        except Exception as e:
            print(f"Anthropic API error: {e}", file=sys.stderr)
        return None
    
    def _openai_request(self, prompt: str) -> Optional[str]:
        """Make request to OpenAI API."""
        try:
            import requests
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.ai_key}'
                },
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1000
                }
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
        except ImportError:
            print("requests library not available for AI conversion", file=sys.stderr)
        except Exception as e:
            print(f"OpenAI API error: {e}", file=sys.stderr)
        return None
    
    def _gemini_request(self, prompt: str) -> Optional[str]:
        """Make request to Google Gemini API."""
        try:
            import requests
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.ai_key}',
                headers={'Content-Type': 'application/json'},
                json={
                    'contents': [{'parts': [{'text': prompt}]}],
                    'generationConfig': {'maxOutputTokens': 1000}
                }
            )
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text'].strip()
        except ImportError:
            print("requests library not available for AI conversion", file=sys.stderr)
        except Exception as e:
            print(f"Gemini API error: {e}", file=sys.stderr)
        return None
    
    def _xai_request(self, prompt: str) -> Optional[str]:
        """Make request to xAI Grok API."""
        try:
            import requests
            response = requests.post(
                'https://api.x.ai/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.ai_key}'
                },
                json={
                    'model': 'grok-beta',
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 1000
                }
            )
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
        except ImportError:
            print("requests library not available for AI conversion", file=sys.stderr)
        except Exception as e:
            print(f"xAI API error: {e}", file=sys.stderr)
        return None
    
    def convert_with_regex(self, sql_query: str) -> Optional[str]:
        """Convert SQL to MongoDB using regex patterns."""
        sql = sql_query.strip().rstrip(';')
        
        # SELECT queries
        select_match = re.match(
            r'SELECT\s+(.+?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?(?:\s+ORDER\s+BY\s+(.+?))?(?:\s+LIMIT\s+(\d+))?$',
            sql, re.IGNORECASE | re.DOTALL
        )
        if select_match:
            fields, table, where, order_by, limit = select_match.groups()
            return self._build_find_query(fields, where, order_by, limit)
        
        # INSERT queries  
        insert_match = re.match(
            r'INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)$',
            sql, re.IGNORECASE
        )
        if insert_match:
            table, columns, values = insert_match.groups()
            return self._build_insert_query(columns, values)
        
        # UPDATE queries
        update_match = re.match(
            r'UPDATE\s+(\w+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+?))?$',
            sql, re.IGNORECASE | re.DOTALL
        )
        if update_match:
            table, set_clause, where = update_match.groups()
            return self._build_update_query(set_clause, where)
        
        # DELETE queries
        delete_match = re.match(
            r'DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?$',
            sql, re.IGNORECASE | re.DOTALL
        )
        if delete_match:
            table, where = delete_match.groups()
            return self._build_delete_query(where)
        
        return None
    
    def _build_find_query(self, fields: str, where: Optional[str], order_by: Optional[str], limit: Optional[str]) -> str:
        """Build MongoDB find query."""
        query_parts = [f"db.{self.collection}.find("]
        
        # Where clause
        if where:
            filter_obj = self._parse_where_clause(where)
            query_parts.append(json.dumps(filter_obj, indent=None))
        else:
            query_parts.append("{}")
        
        # Projection (fields)
        if fields.strip() != '*':
            projection = {}
            for field in fields.split(','):
                field = field.strip()
                projection[field] = 1
            query_parts.append(f", {json.dumps(projection, indent=None)}")
        
        query_parts.append(")")
        
        # Order by
        if order_by:
            sort_obj = {}
            for sort_field in order_by.split(','):
                parts = sort_field.strip().split()
                field_name = parts[0]
                direction = 1 if len(parts) == 1 or parts[1].upper() == 'ASC' else -1
                sort_obj[field_name] = direction
            query_parts.append(f".sort({json.dumps(sort_obj, indent=None)})")
        
        # Limit
        if limit:
            query_parts.append(f".limit({limit})")
        
        return ''.join(query_parts)
    
    def _build_insert_query(self, columns: str, values: str) -> str:
        """Build MongoDB insert query."""
        cols = [col.strip() for col in columns.split(',')]
        vals = [val.strip().strip("'\"") for val in values.split(',')]
        
        doc = {}
        for col, val in zip(cols, vals):
            # Try to convert to appropriate type
            if val.lower() in ('true', 'false'):
                doc[col] = val.lower() == 'true'
            elif val.isdigit():
                doc[col] = int(val)
            else:
                doc[col] = val
        
        return f"db.{self.collection}.insertOne({json.dumps(doc, indent=None)})"
    
    def _build_update_query(self, set_clause: str, where: Optional[str]) -> str:
        """Build MongoDB update query."""
        # Parse SET clause
        update_obj = {"$set": {}}
        for assignment in set_clause.split(','):
            parts = assignment.split('=', 1)
            if len(parts) == 2:
                field = parts[0].strip()
                value = parts[1].strip().strip("'\"")
                
                # Type conversion
                if value.lower() in ('true', 'false'):
                    update_obj["$set"][field] = value.lower() == 'true'
                elif value.isdigit():
                    update_obj["$set"][field] = int(value)
                else:
                    update_obj["$set"][field] = value
        
        # Parse WHERE clause
        filter_obj = {}
        if where:
            filter_obj = self._parse_where_clause(where)
        
        return f"db.{self.collection}.updateMany({json.dumps(filter_obj, indent=None)}, {json.dumps(update_obj, indent=None)})"
    
    def _build_delete_query(self, where: Optional[str]) -> str:
        """Build MongoDB delete query."""
        filter_obj = {}
        if where:
            filter_obj = self._parse_where_clause(where)
        
        return f"db.{self.collection}.deleteMany({json.dumps(filter_obj, indent=None)})"
    
    def _parse_where_clause(self, where: str) -> Dict[str, Any]:
        """Parse SQL WHERE clause to MongoDB filter object."""
        filter_obj = {}
        
        # Simple equality: field = 'value'
        eq_matches = re.findall(r'(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]', where, re.IGNORECASE)
        if not eq_matches:
            # Try without quotes
            eq_matches = re.findall(r'(\w+)\s*=\s*([^\s]+)', where, re.IGNORECASE)
        for field, value in eq_matches:
            # Type conversion
            if value.lower() in ('true', 'false'):
                filter_obj[field] = value.lower() == 'true'
            elif value.isdigit():
                filter_obj[field] = int(value)
            else:
                filter_obj[field] = value
        
        # LIKE patterns: field LIKE '%pattern%'
        like_matches = re.findall(r'(\w+)\s+LIKE\s+[\'"]([^\'\"]+)[\'"]', where, re.IGNORECASE)
        for field, pattern in like_matches:
            # Convert SQL LIKE to MongoDB regex
            mongo_pattern = pattern.replace('%', '.*').replace('_', '.')
            filter_obj[field] = {"$regex": mongo_pattern, "$options": "i"}
        
        return filter_obj
    
    def execute_mongo_query(self, mongo_query: str, dry_run: bool = False) -> bool:
        """Execute the MongoDB query using mongosh."""
        if not self.mongodb_uri:
            print("Error: mongodb_uri environment variable not set", file=sys.stderr)
            return False
        
        if dry_run:
            print(f"[DRY RUN] Would execute: {mongo_query}")
            return True
        
        # Format the query to ensure results are displayed
        if mongo_query.startswith('db.' + self.collection + '.find'):
            # For find queries, add forEach to display results
            formatted_query = f"use {self.database}; {mongo_query}.forEach(printjson)"
        else:
            formatted_query = f"use {self.database}; printjson({mongo_query})"
            
        cmd = [
            'mongosh', self.mongodb_uri,
            '--eval', formatted_query
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                if result.stdout.strip():
                    print(result.stdout)
                return True
            else:
                print(f"MongoDB execution error: {result.stderr}", file=sys.stderr)
                return False
        except Exception as e:
            print(f"Error executing MongoDB query: {e}", file=sys.stderr)
            return False

def main():
    parser = argparse.ArgumentParser(
        description='Convert SQL queries to MongoDB and execute them',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('sql_query', help='SQL query to convert and execute')
    parser.add_argument('--dry-run', '-d', action='store_true', 
                       help='Show the MongoDB query without executing it')
    parser.add_argument('--ai-only', action='store_true',
                       help='Only use AI conversion (fail if no AI available)')
    parser.add_argument('--regex-only', action='store_true', 
                       help='Only use regex conversion (skip AI)')
    
    args = parser.parse_args()
    
    converter = SQLToMongoConverter()
    mongo_query = None
    
    # Try AI conversion first (unless regex-only)
    if not args.regex_only and converter.ai_provider:
        print("Trying AI conversion...", file=sys.stderr)
        mongo_query = converter.convert_with_ai(args.sql_query)
        
        if mongo_query:
            print(f"AI converted: {mongo_query}", file=sys.stderr)
    
    # Fall back to regex conversion (unless AI-only or AI succeeded)
    if not mongo_query and not args.ai_only:
        print("Trying regex conversion...", file=sys.stderr)
        mongo_query = converter.convert_with_regex(args.sql_query)
        
        if mongo_query:
            print(f"Regex converted: {mongo_query}", file=sys.stderr)
    
    if not mongo_query:
        print(f"Error: Could not convert SQL query: {args.sql_query}", file=sys.stderr)
        return 1
    
    # Execute the query
    success = converter.execute_mongo_query(mongo_query, args.dry_run)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
