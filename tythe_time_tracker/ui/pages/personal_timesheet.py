"""
Personal timesheet page for viewing individual employee timesheets.
"""

import streamlit as st
from typing import List

from ...core.services import TimeTrackingService
from ...core.models import TimeEntry
from ...utils.time_utils import TimeUtils
from export_functions import split_shift_by_rate


def format_timesheet_data(entries: List[TimeEntry]) -> List[dict]:
    """Format timesheet entries for display."""
    timesheet_data = []
    
    for entry in entries:
        # Calculate the actual split using our logic
        is_supervisor = (entry.pay_rate_type == 'Supervisor')
        split = split_shift_by_rate(entry.clock_in, entry.clock_out, is_supervisor)
        
        # Create a display string showing the split
        if is_supervisor:
            rate_display = f"Supervisor ({split['Supervisor']}h)"
        elif split['Standard'] > 0 and split['Enhanced'] > 0:
            rate_display = f"Mixed: {split['Standard']}h Standard, {split['Enhanced']}h Enhanced"
        elif split['Enhanced'] > 0:
            rate_display = f"Enhanced ({split['Enhanced']}h)"
        else:
            rate_display = f"Standard ({split['Standard']}h)"
        
        # Convert UTC times to BST for display
        bst_clock_in = TimeUtils.convert_to_bst(entry.clock_in)
        bst_clock_out = TimeUtils.convert_to_bst(entry.clock_out) if entry.clock_out else None
        
        timesheet_data.append({
            "Date": bst_clock_in.strftime('%Y-%m-%d'),
            "Clock-In": bst_clock_in.strftime('%H:%M:%S'),
            "Clock-Out": bst_clock_out.strftime('%H:%M:%S') if bst_clock_out else "🟢 Still Open",
            "Duration": str(entry.clock_out - entry.clock_in).split('.')[0] if entry.clock_out else "In Progress",
            "Pay Rate": rate_display
        })
    
    return timesheet_data


def show() -> None:
    """Display the personal timesheet interface."""
    st.header("📊 Personal Timesheet")
    
    employee_name = st.text_input("Enter your full name to view timesheet:", key="timesheet_name")
    
    if employee_name.strip():
        service = TimeTrackingService()
        entries = service.get_employee_timesheet(employee_name.strip())
        
        if entries:
            st.subheader(f"Timesheet for {employee_name.strip()}")
            
            # Format and display data
            timesheet_data = format_timesheet_data(entries)
            st.dataframe(timesheet_data, use_container_width=True)
        else:
            st.info(f"No time entries found for {employee_name.strip()}")
    else:
        st.info("Please enter your name to view your timesheet") 