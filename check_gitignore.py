#!/usr/bin/env python3
"""
Script to verify that sensitive files are properly ignored by git
"""

import os
import subprocess

def check_git_status():
    """Check what files git sees and verify .env is ignored"""
    print("🔍 Checking git status and .gitignore...")
    
    try:
        # Check if .env file exists
        if os.path.exists('.env'):
            print("✅ .env file exists locally")
        else:
            print("⚠️  .env file doesn't exist yet - you'll need to create it")
        
        # Check git status
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            
            # Check if .env is being tracked
            env_files = [f for f in files if '.env' in f]
            
            if env_files:
                print("❌ WARNING: .env files are being tracked by git!")
                for file in env_files:
                    print(f"   - {file}")
                print("\n🔧 Fix this by running:")
                print("   git rm --cached .env")
                print("   git commit -m 'Remove .env from tracking'")
            else:
                print("✅ .env files are properly ignored by git")
            
            # Show what files are tracked
            tracked_files = [f for f in files if not f.startswith('??')]
            if tracked_files:
                print("\n📁 Files that will be committed:")
                for file in tracked_files:
                    status = file[:2]
                    filename = file[3:]
                    print(f"   {status} {filename}")
            else:
                print("\n📁 No files staged for commit")
                
        else:
            print("❌ Error running git status")
            print(result.stderr)
            
    except FileNotFoundError:
        print("❌ Git not found. Make sure git is installed.")
    except Exception as e:
        print(f"❌ Error: {e}")

def check_gitignore():
    """Check if .gitignore contains the right patterns"""
    print("\n🔍 Checking .gitignore patterns...")
    
    if not os.path.exists('.gitignore'):
        print("❌ .gitignore file not found!")
        return
    
    with open('.gitignore', 'r') as f:
        content = f.read()
    
    required_patterns = ['.env', '__pycache__', 'venv']
    missing_patterns = []
    
    for pattern in required_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing patterns in .gitignore: {missing_patterns}")
    else:
        print("✅ .gitignore contains all required patterns")

if __name__ == "__main__":
    print("🛡️  Git Security Check for The Tythe Barn Time Tracker")
    print("=" * 50)
    
    check_gitignore()
    check_git_status()
    
    print("\n" + "=" * 50)
    print("💡 Remember:")
    print("   - Never commit .env files")
    print("   - Set environment variables in Streamlit Cloud dashboard")
    print("   - Keep your Supabase credentials secure") 