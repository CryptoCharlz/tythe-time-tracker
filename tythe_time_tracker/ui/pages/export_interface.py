"""
Export interface page for timesheet exports.
"""

import streamlit as st
import os
from datetime import datetime, date
from typing import Optional

from ...core.services import TimeTrackingService
from ...utils.time_utils import TimeUtils
from export_functions import (
    get_date_range, get_timesheet_data, export_to_excel, 
    export_to_pdf, calculate_summary, split_shift_by_rate
)


def show_export_access_info() -> None:
    """Show export access information based on user role."""
    is_manager = st.session_state.get('manager_authenticated', False)
    
    if is_manager:
        st.success("👨‍💼 Manager Export Access")
        st.info("You can export timesheets for any employee or the entire team.")
    else:
        st.info("👤 Employee Export Access")
        st.info("You can only export your own timesheet.")


def get_employee_selection() -> Optional[str]:
    """Get employee selection for export."""
    is_manager = st.session_state.get('manager_authenticated', False)
    
    if is_manager:
        col1, col2 = st.columns(2)
        with col1:
            export_type = st.selectbox(
                "Export Type:",
                ["Individual Employee", "All Staff (Bulk Export)"],
                key="export_type"
            )
        
        with col2:
            if export_type == "Individual Employee":
                return st.text_input("Employee Name:", key="export_employee_name")
            else:
                st.info("📊 Bulk export will include all staff members")
                return None
    else:
        return st.text_input("Enter your name:", key="export_employee_name")


def get_date_range_selection() -> tuple[date, date]:
    """Get date range selection from user."""
    st.subheader("📅 Date Range Selection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        date_option = st.selectbox(
            "Quick Options:",
            ["Custom Range", "This Week", "Last Week", "This Month"],
            key="date_option"
        )
    
    with col2:
        if date_option == "Custom Range":
            # Default to current month
            today = date.today()
            first_of_month = today.replace(day=1)
            
            start_date = st.date_input("From Date:", value=first_of_month, key="start_date")
            end_date = st.date_input("To Date:", value=today, key="end_date")
            
            # Validate date range
            if start_date and end_date:
                if end_date < start_date:
                    st.error("❌ End date cannot be before start date!")
                    return None, None
                st.info(f"Custom Range: {start_date} to {end_date}")
            else:
                st.warning("Please select both start and end dates")
                return None, None
        else:
            start_date, end_date = get_date_range(date_option)
            st.info(f"Selected: {start_date} to {end_date}")
    
    return start_date, end_date


def get_export_options() -> tuple[str, str]:
    """Get export format and role filter options."""
    st.subheader("📋 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_format = st.selectbox(
            "Export Format:",
            ["Excel (.xlsx)", "PDF"],
            key="export_format"
        )
    
    with col2:
        is_manager = st.session_state.get('manager_authenticated', False)
        if is_manager:
            role_filter = st.selectbox(
                "Filter by Role:",
                ["All Roles", "Staff Only", "Supervisors Only"],
                key="role_filter"
            )
        else:
            role_filter = "All Roles"
    
    return export_format, role_filter


def show_preview_data(entries: list, start_date: date, end_date: date) -> None:
    """Show preview of export data."""
    if not entries:
        st.warning("No entries found for the selected criteria")
        return
    
    st.success(f"✅ Found {len(entries)} entries")
    
    # Calculate summary
    summary = calculate_summary(entries)
    staff_summary = summary.get('staff_summary', {})
    
    # Display overall summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Hours", f"{summary['total_hours']}")
    with col2:
        st.metric("Total Shifts", f"{summary['total_shifts']}")
    with col3:
        st.metric("Unique Employees", f"{summary['unique_employees']}")
    
    # Preview staff summary data
    st.subheader("📊 Staff Hours Summary")
    if staff_summary:
        preview_data = []
        for employee, data in staff_summary.items():
            preview_data.append({
                "Staff Name": employee,
                "Standard Hours": data['Standard'],
                "Enhanced Hours": data['Enhanced'],
                "Supervisor Hours": data['Supervisor'],
                "Total Hours": data['total_hours'],
                "Total Shifts": data['total_shifts']
            })
        
        st.dataframe(preview_data, use_container_width=True)
        
        # Show detailed shifts in expander
        with st.expander("📋 View Individual Shifts", expanded=False):
            detailed_data = []
            for entry in entries[:20]:  # Show first 20 entries
                entry_id, emp, clock_in, clock_out, pay_rate_type, created_at = entry
                is_supervisor = (pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
                
                # Convert UTC times to BST for display
                bst_clock_in = TimeUtils.convert_to_bst(clock_in)
                bst_clock_out = TimeUtils.convert_to_bst(clock_out) if clock_out else None
                
                detailed_data.append({
                    "Employee": emp,
                    "Date": bst_clock_in.strftime('%Y-%m-%d'),
                    "Clock-In": bst_clock_in.strftime('%H:%M:%S'),
                    "Clock-Out": bst_clock_out.strftime('%H:%M:%S') if bst_clock_out else "In Progress",
                    "Standard Hours": split['Standard'],
                    "Enhanced Hours": split['Enhanced'],
                    "Supervisor Hours": split['Supervisor'],
                    "Total Hours": sum(split.values()),
                    "Pay Rate": pay_rate_type,
                    "Supervisor": "Yes" if pay_rate_type == "Supervisor" else "No"
                })
            st.dataframe(detailed_data, use_container_width=True)
            if len(entries) > 20:
                st.info(f"Showing first 20 of {len(entries)} individual shifts")
    else:
        st.info("No staff summary data available")


def handle_export(entries: list, export_format: str, start_date: date, end_date: date) -> None:
    """Handle the actual export process."""
    if not entries:
        st.warning("No entries found for the selected criteria")
        return
    
    if export_format == "Excel (.xlsx)":
        filename = f"timesheet_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        export_to_excel(entries, filename, start_date, end_date)
        
        with open(filename, "rb") as f:
            st.download_button(
                label="📥 Download Excel File",
                data=f.read(),
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        os.remove(filename)  # Clean up
    else:
        filename = f"timesheet_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        export_to_pdf(entries, filename)
        
        with open(filename, "rb") as f:
            st.download_button(
                label="📥 Download PDF File",
                data=f.read(),
                file_name=filename,
                mime="application/pdf"
            )
        os.remove(filename)  # Clean up


def show() -> None:
    """Display the export interface."""
    st.header("📤 Export Timesheet")
    
    # Show access info
    show_export_access_info()
    st.markdown("---")
    
    # Employee selection
    employee_name = get_employee_selection()
    st.markdown("---")
    
    # Date range selection
    start_date, end_date = get_date_range_selection()
    if start_date is None or end_date is None:
        return
    
    st.markdown("---")
    
    # Export options
    export_format, role_filter = get_export_options()
    st.markdown("---")
    
    # Preview and export
    if st.button("👁️ Preview Data", type="secondary"):
        is_manager = st.session_state.get('manager_authenticated', False)
        
        if not employee_name and not is_manager:
            st.warning("Please enter your name")
            return
        
        # Get data
        entries = get_timesheet_data(
            employee_name=employee_name if employee_name else None,
            start_date=start_date,
            end_date=end_date,
            is_manager=is_manager
        )
        
        if entries:
            show_preview_data(entries, start_date, end_date)
            
            # Export buttons
            st.markdown("---")
            st.subheader("📤 Export")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if export_format == "Excel (.xlsx)":
                    if st.button("📊 Export to Excel", type="primary"):
                        handle_export(entries, export_format, start_date, end_date)
                else:
                    if st.button("📄 Export to PDF", type="primary"):
                        handle_export(entries, export_format, start_date, end_date)
            
            with col2:
                st.info("💡 **Export includes:**\n- Staff name & role\n- Clock-in/out times\n- Total hours worked\n- Applied pay rate\n- Supervisor flag\n- Summary totals")
    
    # Direct export without preview
    st.markdown("---")
    if st.button("🚀 Export Directly", type="primary"):
        is_manager = st.session_state.get('manager_authenticated', False)
        
        if not employee_name and not is_manager:
            st.warning("Please enter your name")
            return
        
        # Get data
        entries = get_timesheet_data(
            employee_name=employee_name if employee_name else None,
            start_date=start_date,
            end_date=end_date,
            is_manager=is_manager
        )
        
        handle_export(entries, export_format, start_date, end_date) 