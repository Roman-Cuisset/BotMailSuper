#!/usr/bin/env python3
"""
One-time authorization script for Google Drive
Run this once to authorize the bot to access your Google Drive
"""
from utils.drive_manager import get_drive_service

if __name__ == "__main__":
    print("🔐 Authorizing Google Drive access...")
    print("A browser window will open. Please log in and authorize the app.")
    print()
    
    try:
        service = get_drive_service()
        print("✅ Authorization successful!")
        print("Token saved to token.pickle")
        print()
        print("You can now use Google Drive integration in the bot.")
    except Exception as e:
        print(f"❌ Authorization failed: {e}")
