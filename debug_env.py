#!/usr/bin/env python3
"""
Debug script to check .env file loading
"""

import os
from dotenv import load_dotenv

print("🔍 Debugging .env file loading...")
print("=" * 50)

# Load environment variables
load_dotenv()

# Check if .env file exists
if os.path.exists('.env'):
    print("✅ .env file exists")
else:
    print("❌ .env file NOT found!")
    print("   Make sure you created .env (not env.example)")

print("\n📋 Environment variables:")
print(f"SUPABASE_HOST: '{os.getenv('SUPABASE_HOST')}'")
print(f"SUPABASE_DATABASE: '{os.getenv('SUPABASE_DATABASE')}'")
print(f"SUPABASE_USER: '{os.getenv('SUPABASE_USER')}'")
print(f"SUPABASE_PASSWORD: '{os.getenv('SUPABASE_PASSWORD', '***HIDDEN***')}'")
print(f"SUPABASE_PORT: '{os.getenv('SUPABASE_PORT')}'")

print("\n🔍 Issues to check:")
if not os.getenv('SUPABASE_HOST'):
    print("❌ SUPABASE_HOST is empty or None")
if not os.getenv('SUPABASE_USER'):
    print("❌ SUPABASE_USER is empty or None")
if not os.getenv('SUPABASE_PASSWORD'):
    print("❌ SUPABASE_PASSWORD is empty or None")
if not os.getenv('SUPABASE_PORT'):
    print("❌ SUPABASE_PORT is empty or None")

print("\n💡 If any values are None or empty:")
print("   1. Check your .env file exists")
print("   2. Check the format: KEY=value (no spaces around =)")
print("   3. Make sure you're using the Direct connection values from Supabase") 