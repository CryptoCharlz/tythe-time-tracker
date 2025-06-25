"""
Main Streamlit application module.

This module handles the core app configuration, navigation, and main layout.
"""

import streamlit as st
from typing import Optional

from ..config.settings import get_app_config
from ..database.init import ensure_database_ready
from .pages import (
    employee_interface,
    personal_timesheet,
    export_interface,
    manager_dashboard
)


def setup_page_config() -> None:
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="The Tythe Barn - Time Tracker",
        page_icon="🕒",
        layout="wide"
    )


def initialize_database() -> None:
    """Initialize the database on app startup."""
    if not ensure_database_ready():
        st.error("❌ Failed to initialize database. Please check your configuration.")
        st.stop()


def show_pay_rate_info() -> None:
    """Display pay rate information in an expander."""
    with st.expander("💰 Pay Rate Information", expanded=False):
        st.markdown("""
        **Pay Rate Rules:**
        - **Standard Rate:** Regular hours (4:00 AM - 7:00 PM)
        - **Enhanced Rate:** Night hours (7:00 PM - 4:00 AM) 
        - **Supervisor Rate:** When supervisor role is selected (overrides other rates)
        
        **Note:** If you clock in during enhanced hours AND select supervisor role, you'll receive the supervisor rate.
        """)


def show_navigation() -> str:
    """Display navigation sidebar and return selected page."""
    return st.sidebar.selectbox(
        "Choose a page:",
        ["Employee Clock In/Out", "Personal Timesheet", "Export Timesheet", "Manager Dashboard"]
    )


def show_version_info() -> None:
    """Display version information in the sidebar."""
    config = get_app_config()
    st.sidebar.markdown(
        f"<div style='text-align:right; color: #888; font-size: 0.9em;'>Version: {config.version}</div>",
        unsafe_allow_html=True
    )


def route_to_page(page: str) -> None:
    """Route to the appropriate page based on selection."""
    if page == "Employee Clock In/Out":
        employee_interface.show()
    elif page == "Personal Timesheet":
        personal_timesheet.show()
    elif page == "Export Timesheet":
        export_interface.show()
    elif page == "Manager Dashboard":
        manager_dashboard.show()


def main() -> None:
    """Main application entry point."""
    # Setup page configuration
    setup_page_config()
    
    # Initialize database
    initialize_database()
    
    # Main title
    st.title("🕒 The Tythe Barn - Time Tracker")
    st.markdown("---")
    
    # Show pay rate information
    show_pay_rate_info()
    
    # Navigation
    selected_page = show_navigation()
    
    # Route to selected page
    route_to_page(selected_page)
    
    # Show version info
    show_version_info()


if __name__ == "__main__":
    main() 