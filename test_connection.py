#!/usr/bin/env python3
"""
Test script to verify database connection and table creation
"""

import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test database connection and table creation"""
    print("🔍 Testing database connection...")
    
    try:
        # Test connection
        conn = psycopg2.connect(
            host=os.getenv('SUPABASE_HOST'),
            database=os.getenv('SUPABASE_DATABASE'),
            user=os.getenv('SUPABASE_USER'),
            password=os.getenv('SUPABASE_PASSWORD'),
            port=os.getenv('SUPABASE_PORT', '5432'),
            # Force IPv4 connection to avoid IPv6 issues
            options='-c family=ipv4'
        )
        
        print("✅ Database connection successful!")
        
        # Test table creation
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                employee TEXT NOT NULL,
                clock_in TIMESTAMPTZ NOT NULL,
                clock_out TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)
        conn.commit()
        
        print("✅ Table creation/verification successful!")
        
        # Test a simple query
        cursor.execute("SELECT COUNT(*) FROM time_entries")
        count = cursor.fetchone()[0]
        print(f"✅ Database query successful! Current entries: {count}")
        
        cursor.close()
        conn.close()
        
        print("\n🎉 All tests passed! Your database is ready to use.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Check your .env file has correct Supabase credentials")
        print("2. Verify your Supabase project is active")
        print("3. Ensure your IP is allowed in Supabase settings")
        return False

if __name__ == "__main__":
    test_connection() 