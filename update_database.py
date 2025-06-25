#!/usr/bin/env python3
"""
Script to update database schema for pay rate functionality
"""

import streamlit as st
import psycopg2

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            host=st.secrets["SUPABASE"]["HOST"],
            database=st.secrets["SUPABASE"]["DATABASE"],
            user=st.secrets["SUPABASE"]["USER"],
            password=st.secrets["SUPABASE"]["PASSWORD"],
            port=st.secrets["SUPABASE"]["PORT"],
            options='-c family=ipv4'
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None

def update_database_schema():
    """Add pay_rate_type column to time_entries table"""
    print("🔧 Updating database schema...")
    
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to database")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'time_entries' 
            AND column_name = 'pay_rate_type'
        """)
        
        if cursor.fetchone():
            print("✅ pay_rate_type column already exists")
        else:
            # Add the new column
            cursor.execute("""
                ALTER TABLE time_entries 
                ADD COLUMN pay_rate_type TEXT DEFAULT 'Standard'
            """)
            conn.commit()
            print("✅ Added pay_rate_type column to time_entries table")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error updating database: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return False

if __name__ == "__main__":
    # This script needs to be run in Streamlit context to access secrets
    print("Please run this update from within the Streamlit app")
    print("The database will be updated automatically when you restart the app") 