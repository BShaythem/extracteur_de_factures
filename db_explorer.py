#!/usr/bin/env python3
"""
Interactive Database Explorer
A more advanced tool for exploring and monitoring your SQLite database.
"""

import sqlite3
import json
import os
from datetime import datetime

class DatabaseExplorer:
    def __init__(self, db_path='invoices.db'):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Connect to the database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # This allows accessing columns by name
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the database"""
        if self.conn:
            self.conn.close()
    
    def get_tables(self):
        """Get all tables in the database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_info(self, table_name):
        """Get detailed information about a table"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        return cursor.fetchall()
    
    def get_table_data(self, table_name, limit=50, offset=0):
        """Get data from a table with pagination"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}")
        return cursor.fetchall()
    
    def get_table_count(self, table_name):
        """Get the total number of rows in a table"""
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    
    def execute_custom_query(self, query):
        """Execute a custom SQL query"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            return f"Error: {e}"
    
    def show_menu(self):
        """Show the main menu"""
        print("\n" + "="*60)
        print("🔍 DATABASE EXPLORER")
        print("="*60)
        print("1. Show database overview")
        print("2. Explore table structure")
        print("3. View table data")
        print("4. Execute custom query")
        print("5. Show recent invoices")
        print("6. Show user statistics")
        print("0. Exit")
        print("-"*60)
    
    def show_overview(self):
        """Show database overview"""
        print("\n📊 DATABASE OVERVIEW")
        print("-" * 40)
        
        tables = self.get_tables()
        total_records = 0
        
        for table in tables:
            count = self.get_table_count(table)
            total_records += count
            print(f"📋 {table}: {count} records")
        
        print(f"\n📈 Total records across all tables: {total_records}")
        
        # Show database file info
        if os.path.exists(self.db_path):
            size = os.path.getsize(self.db_path)
            print(f"💾 Database file size: {size:,} bytes ({size/1024:.1f} KB)")
    
    def explore_table_structure(self):
        """Explore the structure of a specific table"""
        tables = self.get_tables()
        
        print("\n📋 Available tables:")
        for i, table in enumerate(tables, 1):
            print(f"{i}. {table}")
        
        try:
            choice = int(input("\nSelect table number: ")) - 1
            if 0 <= choice < len(tables):
                table_name = tables[choice]
                self.show_table_structure(table_name)
            else:
                print("Invalid selection!")
        except ValueError:
            print("Please enter a valid number!")
    
    def show_table_structure(self, table_name):
        """Show detailed structure of a table"""
        print(f"\n🏗️  TABLE STRUCTURE: {table_name}")
        print("-" * 60)
        
        columns = self.get_table_info(table_name)
        print(f"{'Column':<20} {'Type':<15} {'Not Null':<10} {'Primary Key':<12}")
        print("-" * 60)
        
        for col in columns:
            not_null = "YES" if col[3] else "NO"
            primary_key = "YES" if col[5] else "NO"
            print(f"{col[1]:<20} {col[2]:<15} {not_null:<10} {primary_key:<12}")
    
    def view_table_data(self):
        """View data from a specific table"""
        tables = self.get_tables()
        
        print("\n📋 Available tables:")
        for i, table in enumerate(tables, 1):
            count = self.get_table_count(table)
            print(f"{i}. {table} ({count} records)")
        
        try:
            choice = int(input("\nSelect table number: ")) - 1
            if 0 <= choice < len(tables):
                table_name = tables[choice]
                self.show_table_data(table_name)
            else:
                print("Invalid selection!")
        except ValueError:
            print("Please enter a valid number!")
    
    def show_table_data(self, table_name, limit=20):
        """Show data from a table"""
        print(f"\n📊 DATA FROM: {table_name}")
        print("-" * 60)
        
        # Get column names
        columns = [col[1] for col in self.get_table_info(table_name)]
        
        # Get data
        rows = self.get_table_data(table_name, limit)
        
        if not rows:
            print("No data found in this table.")
            return
        
        # Print headers
        header = " | ".join(f"{col:<20}" for col in columns)
        print(header)
        print("-" * len(header))
        
        # Print data
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
        
        total = self.get_table_count(table_name)
        print(f"\nShowing {len(rows)} of {total} records")
    
    def execute_custom_query(self):
        """Execute a custom SQL query"""
        print("\n🔍 CUSTOM QUERY")
        print("-" * 40)
        print("Enter your SQL query (or 'back' to return):")
        
        query = input("SQL> ").strip()
        if query.lower() == 'back':
            return
        
        if not query:
            print("No query entered!")
            return
        
        result = self.execute_custom_query(query)
        
        if isinstance(result, str):
            print(f"❌ {result}")
        else:
            print(f"\n✅ Query executed successfully!")
            print(f"📊 Results: {len(result)} rows")
            
            if result:
                # Show first few results
                for i, row in enumerate(result[:10]):
                    print(f"\nRow {i+1}:")
                    for key in row.keys():
                        print(f"  {key}: {row[key]}")
                
                if len(result) > 10:
                    print(f"\n... and {len(result) - 10} more rows")
    
    def show_recent_invoices(self):
        """Show recent invoices with details"""
        print("\n📄 RECENT INVOICES")
        print("-" * 60)
        
        query = """
        SELECT i.id, i.method, i.created_at, u.username,
               json_extract(i.extracted_fields, '$.invoice_number.selected') as invoice_number,
               json_extract(i.extracted_fields, '$.supplier_name.selected') as supplier_name,
               json_extract(i.extracted_fields, '$.invoice_total.selected') as total
        FROM invoices i
        JOIN users u ON i.user_id = u.id
        ORDER BY i.created_at DESC
        LIMIT 10
        """
        
        result = self.execute_custom_query(query)
        
        if isinstance(result, str):
            print(f"❌ {result}")
            return
        
        if not result:
            print("No invoices found in the database.")
            return
        
        print(f"{'ID':<5} {'Method':<12} {'Invoice #':<15} {'Supplier':<20} {'Total':<10} {'User':<10} {'Date'}")
        print("-" * 80)
        
        for row in result:
            invoice_num = row['invoice_number'] or 'N/A'
            supplier = row['supplier_name'] or 'N/A'
            total = row['total'] or 'N/A'
            date = row['created_at'][:10] if row['created_at'] else 'N/A'
            
            print(f"{row['id']:<5} {row['method']:<12} {invoice_num:<15} {supplier:<20} {total:<10} {row['username']:<10} {date}")
    
    def show_user_statistics(self):
        """Show user statistics"""
        print("\n👥 USER STATISTICS")
        print("-" * 40)
        
        # Get user count
        user_count = self.get_table_count('users')
        print(f"📊 Total users: {user_count}")
        
        # Get invoice count per user
        query = """
        SELECT u.username, COUNT(i.id) as invoice_count
        FROM users u
        LEFT JOIN invoices i ON u.id = i.user_id
        GROUP BY u.id, u.username
        ORDER BY invoice_count DESC
        """
        
        result = self.execute_custom_query(query)
        
        if isinstance(result, str):
            print(f"❌ {result}")
            return
        
        print(f"\n📄 Invoices per user:")
        print(f"{'Username':<15} {'Invoices':<10}")
        print("-" * 25)
        
        for row in result:
            print(f"{row['username']:<15} {row['invoice_count']:<10}")
    
    def run(self):
        """Run the interactive explorer"""
        if not self.connect():
            return
        
        try:
            while True:
                self.show_menu()
                choice = input("Enter your choice (0-6): ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    self.show_overview()
                elif choice == '2':
                    self.explore_table_structure()
                elif choice == '3':
                    self.view_table_data()
                elif choice == '4':
                    self.execute_custom_query()
                elif choice == '5':
                    self.show_recent_invoices()
                elif choice == '6':
                    self.show_user_statistics()
                else:
                    print("❌ Invalid choice! Please enter a number between 0-6.")
                
                input("\nPress Enter to continue...")
        
        finally:
            self.disconnect()

if __name__ == "__main__":
    explorer = DatabaseExplorer()
    explorer.run()
