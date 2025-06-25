"""
The Tythe Barn Time Tracker - Main Application Entry Point

This is the main entry point for the Streamlit application.
The actual UI logic has been modularized into the tythe_time_tracker.ui package.
"""

import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import and run the main application
from tythe_time_tracker.ui.app import main

if __name__ == "__main__":
    main()
