"""
Manager dashboard page for administrative functions.
"""

import streamlit as st
import os
from datetime import datetime, date, time
from typing import Optional, Tuple
from collections import defaultdict

from ...core.services import TimeTrackingService
from ...core.models import TimeEntry
from ...config.settings import get_app_config
from export_functions import (
    export_to_excel, export_to_pdf, split_shift_by_rate
)


def handle_manager_authentication() -> bool:
    """Handle manager authentication."""
    if 'manager_authenticated' not in st.session_state:
        st.session_state.manager_authenticated = False
    
    if not st.session_state.manager_authenticated:
        st.header("👨‍💼 Manager Dashboard")
        password = st.text_input("Enter manager password:", type="password")
        if st.button("Login"):
            config = get_app_config()
            if password == config.manager_password:
                st.session_state.manager_authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Incorrect password")
        return False
    
    return True


def show_manager_header() -> None:
    """Show manager dashboard header."""
    st.header("👨‍💼 Manager Dashboard")
    st.success("✅ Manager access granted")
    
    if st.button("Logout"):
        st.session_state.manager_authenticated = False
        st.rerun()


def show_all_entries_tab() -> None:
    """Show the 'View All Entries' tab."""
    st.subheader("All Time Entries (Grouped)")
    
    service = TimeTrackingService()
    entries = service.get_all_timesheets()
    
    if not entries:
        st.info("No time entries found")
        return
    
    # Quick Export section
    st.markdown("### Quick Export")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📊 Export All to Excel", key="quick_excel_grouped"):
            filename = f"all_timesheets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            export_to_excel(entries, filename, None, None)
            with open(filename, "rb") as f:
                st.download_button(
                    label="📥 Download Excel File",
                    data=f.read(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            os.remove(filename)
    with col2:
        if st.button("📄 Export All to PDF", key="quick_pdf_grouped"):
            filename = f"all_timesheets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            export_to_pdf(entries, filename)
            with open(filename, "rb") as f:
                st.download_button(
                    label="📥 Download PDF File",
                    data=f.read(),
                    file_name=filename,
                    mime="application/pdf"
                )
            os.remove(filename)
    
    # Group by staff
    staff_shifts = defaultdict(list)
    for entry in entries:
        staff_shifts[entry.employee.strip()].append(entry)
    
    for staff, shifts in sorted(staff_shifts.items()):
        with st.expander(f"{staff}", expanded=False):
            # Staff summary
            total_std = total_enh = total_sup = total_hours = 0
            for entry in shifts:
                is_supervisor = (entry.pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(entry.clock_in, entry.clock_out, is_supervisor)
                total_std += split['Standard']
                total_enh += split['Enhanced']
                total_sup += split['Supervisor']
                total_hours += sum(split.values())
            
            st.markdown(f"**Total:** {total_hours:.2f}h  ")
            st.markdown(f"Standard: {total_std:.2f}h | Enhanced: {total_enh:.2f}h | Supervisor: {total_sup:.2f}h")
            st.markdown("---")
            
            # List shifts
            for entry in sorted(shifts, key=lambda e: e.clock_in, reverse=True):
                is_supervisor = (entry.pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(entry.clock_in, entry.clock_out, is_supervisor)
                
                if is_supervisor:
                    rate_display = f"Supervisor ({split['Supervisor']}h)"
                elif split['Standard'] > 0 and split['Enhanced'] > 0:
                    rate_display = f"Mixed: {split['Standard']}h Standard, {split['Enhanced']}h Enhanced"
                elif split['Enhanced'] > 0:
                    rate_display = f"Enhanced ({split['Enhanced']}h)"
                else:
                    rate_display = f"Standard ({split['Standard']}h)"
                
                col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 3, 1])
                with col1:
                    st.markdown(entry.clock_in.strftime('%Y-%m-%d'))
                with col2:
                    st.markdown(entry.clock_in.strftime('%H:%M'))
                with col3:
                    st.markdown(entry.clock_out.strftime('%H:%M') if entry.clock_out else 'In Progress')
                with col4:
                    st.markdown(rate_display)
                with col5:
                    if st.button("✏️", key=f"edit_{entry.id}"):
                        st.session_state['edit_entry_id'] = str(entry.id)
                        st.session_state['__active_tab__'] = 2
                    if st.button("🗑️", key=f"delete_{entry.id}"):
                        st.session_state['delete_entry_id'] = str(entry.id)
                        st.session_state['__active_tab__'] = 3


def show_add_shift_tab() -> None:
    """Show the 'Add Shift' tab."""
    st.subheader("➕ Add Shift Manually")
    
    col1, col2 = st.columns(2)
    
    with col1:
        employee_name = st.text_input("Employee Name:", key="add_employee")
        clock_in_date = st.date_input("Clock-In Date:", key="add_clock_in_date")
        clock_in_time = st.time_input("Clock-In Time:", key="add_clock_in_time")
        is_supervisor = st.checkbox("👑 Supervisor Role", key="add_supervisor")
    
    with col2:
        clock_out_date = st.date_input("Clock-Out Date (optional):", key="add_clock_out_date")
        clock_out_time = st.time_input("Clock-Out Time (optional):", key="add_clock_out_time")
        
        pay_rate_override = st.selectbox(
            "Pay Rate Override (optional):",
            ["Auto-calculate", "Standard", "Enhanced", "Supervisor"],
            key="add_pay_rate_override"
        )
        
        if pay_rate_override == "Auto-calculate":
            pay_rate_override = None
    
    if st.button("➕ Add Shift", type="primary"):
        if employee_name.strip():
            service = TimeTrackingService()
            success, message = service.add_shift_manually(
                employee_name.strip(),
                clock_in_date,
                clock_in_time,
                clock_out_date if clock_out_date else None,
                clock_out_time if clock_out_time else None,
                is_supervisor,
                pay_rate_override
            )
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Please enter an employee name")


def show_edit_shift_tab() -> None:
    """Show the 'Edit Shift' tab."""
    st.subheader("✏️ Edit Shift")
    
    # Show instructions first
    st.info("💡 **Instructions:** Copy an Entry ID from the 'View All Entries' tab above, then paste it here to edit that shift.")
    
    # Get shift to edit
    entry_id = st.text_input("Enter Entry ID to edit:", key="edit_entry_id", placeholder="Paste Entry ID here...")
    
    if not entry_id:
        st.warning("Please enter an Entry ID to edit a shift")
        return
    
    service = TimeTrackingService()
    shift = service.get_shift_by_id(entry_id)
    
    if not shift:
        st.error("❌ Shift not found. Please check the Entry ID.")
        st.info("💡 Make sure you copied the Entry ID correctly from the 'View All Entries' tab.")
        return
    
    st.success(f"✅ Found shift for {shift.employee}")
    
    # Debug info (can be removed later)
    with st.expander("🔍 Debug Info", expanded=False):
        st.write(f"Entry ID: {shift.id}")
        st.write(f"Employee: {shift.employee}")
        st.write(f"Clock In: {shift.clock_in}")
        st.write(f"Clock Out: {shift.clock_out}")
        st.write(f"Pay Rate: {shift.pay_rate_type}")
    
    st.markdown("---")
    st.subheader("Edit Shift Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        employee_name = st.text_input("Employee Name:", value=shift.employee, key="edit_employee")
        clock_in_date = st.date_input("Clock-In Date:", value=shift.clock_in.date(), key="edit_clock_in_date")
        clock_in_time = st.time_input("Clock-In Time:", value=shift.clock_in.time(), key="edit_clock_in_time")
        is_supervisor = st.checkbox("👑 Supervisor Role", value=shift.pay_rate_type == "Supervisor", key="edit_supervisor")
    
    with col2:
        # Handle None clock_out values properly
        if shift.clock_out:
            default_clock_out_date = shift.clock_out.date()
            default_clock_out_time = shift.clock_out.time()
        else:
            default_clock_out_date = None
            default_clock_out_time = None
        
        clock_out_date = st.date_input("Clock-Out Date (optional):", value=default_clock_out_date, key="edit_clock_out_date")
        clock_out_time = st.time_input("Clock-Out Time (optional):", value=default_clock_out_time, key="edit_clock_out_time")
        
        pay_rate_override = st.selectbox(
            "Pay Rate Override:",
            ["Auto-calculate", "Standard", "Enhanced", "Supervisor"],
            index=["Auto-calculate", "Standard", "Enhanced", "Supervisor"].index(shift.pay_rate_type) if shift.pay_rate_type in ["Standard", "Enhanced", "Supervisor"] else 0,
            key="edit_pay_rate_override"
        )
        
        if pay_rate_override == "Auto-calculate":
            pay_rate_override = None
    
    if st.button("✏️ Update Shift", type="primary"):
        if employee_name.strip():
            success, message = service.edit_shift(
                entry_id,
                employee_name.strip(),
                clock_in_date,
                clock_in_time,
                clock_out_date if clock_out_date else None,
                clock_out_time if clock_out_time else None,
                is_supervisor,
                pay_rate_override
            )
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Please enter an employee name")


def show_delete_entry_tab() -> None:
    """Show the 'Delete Entry' tab."""
    st.subheader("🗑️ Delete Entry")
    entry_to_delete = st.text_input("Enter Entry ID to delete:", key="delete_entry_id")
    if st.button("🗑️ Delete Entry", type="secondary"):
        if entry_to_delete:
            service = TimeTrackingService()
            success, message = service.delete_entry(entry_to_delete)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
        else:
            st.warning("Please enter an Entry ID")


def show() -> None:
    """Display the manager dashboard."""
    # Handle authentication
    if not handle_manager_authentication():
        return
    
    # Show header
    show_manager_header()
    
    # Manager controls tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 View All Entries", "➕ Add Shift", "✏️ Edit Shift", "🗑️ Delete Entry"])
    
    with tab1:
        show_all_entries_tab()
    
    with tab2:
        show_add_shift_tab()
    
    with tab3:
        show_edit_shift_tab()
    
    with tab4:
        show_delete_entry_tab() 