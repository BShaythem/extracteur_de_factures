#!/usr/bin/env python3
"""
Database Monitor Script
This script helps you view and monitor the contents of your SQLite database.
"""

import sqlite3
import json
from datetime import datetime

def connect_db():
    """Connect to the database"""
    try:
        conn = sqlite3.connect('invoices.db')
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def show_tables(conn):
    """Show all tables in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("\n=== DATABASE TABLES ===")
    for table in tables:
        print(f"- {table[0]}")
    print()

def show_table_schema(conn, table_name):
    """Show the schema of a specific table"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    
    print(f"\n=== SCHEMA FOR TABLE: {table_name} ===")
    print(f"{'Column':<20} {'Type':<15} {'Not Null':<10} {'Primary Key':<12} {'Default'}")
    print("-" * 70)
    for col in columns:
        print(f"{col[1]:<20} {col[2]:<15} {col[3]:<10} {col[5]:<12} {col[4]}")
    print()

def show_table_data(conn, table_name, limit=10):
    """Show data from a specific table"""
    cursor = conn.cursor()
    
    # Get column names
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    
    # Get data
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
    rows = cursor.fetchall()
    
    print(f"\n=== DATA FROM TABLE: {table_name} ===")
    if not rows:
        print("No data found in this table.")
        return
    
    # Print column headers
    print(" | ".join(f"{col:<20}" for col in columns))
    print("-" * (len(columns) * 23))
    
    # Print data rows
    for row in rows:
        formatted_row = []
        for value in row:
            if value is None:
                formatted_row.append("NULL")
            elif isinstance(value, str) and len(value) > 18:
                formatted_row.append(f"{value[:15]}...")
            else:
                formatted_row.append(str(value))
        print(" | ".join(f"{val:<20}" for val in formatted_row))
    
    # Show total count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    total = cursor.fetchone()[0]
    print(f"\nTotal rows: {total}")
    if total > limit:
        print(f"Showing first {limit} rows. Use --limit to see more.")

def show_database_summary(conn):
    """Show a summary of the database"""
    cursor = conn.cursor()
    
    print("\n=== DATABASE SUMMARY ===")
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"{table_name}: {count} rows")
    
    print()

def main():
    """Main function"""
    print("🔍 Database Monitor")
    print("=" * 50)
    
    conn = connect_db()
    if not conn:
        return
    
    try:
        # Show database summary
        show_database_summary(conn)
        
        # Show all tables
        show_tables(conn)
        
        # Show detailed data for each table
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            show_table_schema(conn, table_name)
            show_table_data(conn, table_name)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
