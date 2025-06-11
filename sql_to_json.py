#!/usr/bin/env python3
"""
SQLite Database Schema to JSON Extractor

This script extracts the complete schema from an SQLite database
and saves it as a comprehensive JSON file.
"""

import sqlite3
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


class SQLiteSchemaExtractor:
    def __init__(self, db_path: str):
        """Initialize the schema extractor with database path."""
        self.db_path = db_path
        self.connection = None
        self.cursor = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connection = sqlite3.connect(self.db_path)
        self.cursor = self.connection.cursor()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.connection:
            self.connection.close()
    
    def get_tables(self) -> List[str]:
        """Get all table names from the database."""
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row[0] for row in self.cursor.fetchall()]
    
    def quote_identifier(self, identifier: str) -> str:
        """Properly quote an identifier to handle special characters."""
        return f'"{identifier}"'
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column information for a specific table."""
        self.cursor.execute(f"PRAGMA table_info({self.quote_identifier(table_name)})")
        columns = []
        for row in self.cursor.fetchall():
            columns.append({
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "default_value": row[4],
                "pk": bool(row[5])
            })
        return columns
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign key information for a specific table."""
        self.cursor.execute(f"PRAGMA foreign_key_list({self.quote_identifier(table_name)})")
        foreign_keys = []
        for row in self.cursor.fetchall():
            foreign_keys.append({
                "id": row[0],
                "seq": row[1],
                "table": row[2],
                "from": row[3],
                "to": row[4],
                "on_update": row[5],
                "on_delete": row[6],
                "match": row[7]
            })
        return foreign_keys
    
    def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get index information for a specific table."""
        # Use parameterized query to avoid SQL injection
        self.cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name=?",
            (table_name,)
        )
        indexes = []
        for row in self.cursor.fetchall():
            index_name = row[0]
            index_sql = row[1]
            
            if index_name is None:  # Skip auto-generated indexes
                continue
                
            try:
                # Get detailed index info
                self.cursor.execute(f"PRAGMA index_info({self.quote_identifier(index_name)})")
                columns = [col[2] for col in self.cursor.fetchall()]
                
                # Check if index is unique
                self.cursor.execute(f"PRAGMA index_list({self.quote_identifier(table_name)})")
                unique = False
                for idx_row in self.cursor.fetchall():
                    if idx_row[1] == index_name:
                        unique = bool(idx_row[2])
                        break
                
                indexes.append({
                    "name": index_name,
                    "unique": unique,
                    "columns": columns,
                    "sql": index_sql
                })
            except sqlite3.Error:
                # Skip problematic indexes
                continue
                
        return indexes
    
    def get_triggers(self, table_name: str) -> List[Dict[str, Any]]:
        """Get trigger information for a specific table."""
        # Use parameterized query
        self.cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?",
            (table_name,)
        )
        triggers = []
        for row in self.cursor.fetchall():
            triggers.append({
                "name": row[0],
                "sql": row[1]
            })
        return triggers
    
    def get_table_sql(self, table_name: str) -> Optional[str]:
        """Get the CREATE TABLE statement for a specific table."""
        # Use parameterized query
        self.cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_views(self) -> List[Dict[str, Any]]:
        """Get all views from the database."""
        self.cursor.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='view'"
        )
        views = []
        for row in self.cursor.fetchall():
            views.append({
                "name": row[0],
                "sql": row[1]
            })
        return views
    
    def extract_schema(self) -> Dict[str, Any]:
        """Extract complete database schema."""
        schema = {
            "database": {
                "path": self.db_path,
                "sqlite_version": sqlite3.sqlite_version
            },
            "tables": {},
            "views": []
        }
        
        # Get all tables
        tables = self.get_tables()
        
        for table in tables:
            try:
                table_schema = {
                    "columns": self.get_table_info(table),
                    "foreign_keys": self.get_foreign_keys(table),
                    "indexes": self.get_indexes(table),
                    "triggers": self.get_triggers(table),
                    "create_sql": self.get_table_sql(table)
                }
                
                # Add primary key info
                primary_keys = [col["name"] for col in table_schema["columns"] if col["pk"]]
                table_schema["primary_keys"] = primary_keys
                
                schema["tables"][table] = table_schema
            except sqlite3.Error as e:
                print(f"Warning: Error processing table '{table}': {e}")
                # Still add the table with minimal info
                schema["tables"][table] = {
                    "error": str(e),
                    "columns": [],
                    "foreign_keys": [],
                    "indexes": [],
                    "triggers": [],
                    "primary_keys": [],
                    "create_sql": None
                }
        
        # Get views
        schema["views"] = self.get_views()
        
        return schema


def main():
    """Main function to run the schema extractor."""
    if len(sys.argv) < 2:
        print("Usage: python sql_to_json.py <database_path> [output_json_path]")
        sys.exit(1)
    
    db_path = sys.argv[1]
    
    # Check if database exists
    if not Path(db_path).exists():
        db_path = "databasevf.db"
    
    # Determine output path
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        db_name = Path(db_path).stem
        output_path = f"{db_name}_schema.json"
    
    try:
        # Extract schema
        with SQLiteSchemaExtractor(db_path) as extractor:
            schema = extractor.extract_schema()
        # Save to JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Schema extracted successfully!")
        print(f"✓ Output saved to: {output_path}")
        print(f"✓ Found {len(schema['tables'])} tables and {len(schema['views'])} views")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()