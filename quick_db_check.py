#!/usr/bin/env python3
"""
Quick Database Check
A simple script for quick database status checks.
"""

import sqlite3
import os
from datetime import datetime

def quick_check():
    """Perform a quick check of the database"""
    print("🔍 Quick Database Check")
    print("=" * 40)
    
    # Check if database exists
    if not os.path.exists('invoices.db'):
        print("❌ Database file 'invoices.db' not found!")
        return
    
    # Get file size
    size = os.path.getsize('invoices.db')
    print(f"💾 Database size: {size:,} bytes ({size/1024:.1f} KB)")
    
    try:
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        
        # Get table count
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📋 Tables: {len(tables)}")
        
        # Check each table
        total_records = 0
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            total_records += count
            print(f"  - {table_name}: {count} records")
        
        print(f"\n📊 Total records: {total_records}")
        
        # Check for recent activity
        if 'invoices' in [t[0] for t in tables]:
            cursor.execute("SELECT MAX(created_at) FROM invoices")
            last_invoice = cursor.fetchone()[0]
            if last_invoice:
                print(f"📅 Last invoice: {last_invoice}")
            else:
                print("📅 No invoices yet")
        
        if 'users' in [t[0] for t in tables]:
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"👥 Users: {user_count}")
        
        conn.close()
        print("\n✅ Database check completed successfully!")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    quick_check()
