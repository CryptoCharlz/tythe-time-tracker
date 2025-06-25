import streamlit as st
import psycopg2
import os
from datetime import datetime, date, timezone, timedelta
import uuid
from dotenv import load_dotenv
from export_functions import (
    get_date_range, get_timesheet_data, export_to_excel, 
    export_to_pdf, get_download_link, calculate_summary, split_shift_by_rate
)

# Load environment variables
load_dotenv()

# Timezone handling
def get_bst_time(utc_time=None):
    """Convert UTC time to BST (British Summer Time)"""
    if utc_time is None:
        utc_time = datetime.now(timezone.utc)
    
    # BST is UTC+1, but we need to handle DST properly
    # For simplicity, we'll use UTC+1 for BST (this covers most of the year)
    # In production, you might want to use pytz for more accurate DST handling
    bst_offset = timedelta(hours=1)
    bst_time = utc_time + bst_offset
    
    return bst_time

def is_bst_enhanced_hours(clock_in_time):
    """Check if clock-in time is during enhanced hours in BST"""
    # Convert to BST if it's UTC
    if clock_in_time.tzinfo is None:
        # Assume it's UTC if no timezone info
        clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)
    
    bst_time = get_bst_time(clock_in_time)
    hour = bst_time.hour
    
    # Enhanced rate: 7:00 PM (19:00) to 4:00 AM (04:00) in BST
    if hour >= 19 or hour < 4:
        return True
    else:
        return False

# Page configuration
st.set_page_config(
    page_title="The Tythe Barn - Time Tracker",
    page_icon="🕒",
    layout="wide"
)

# Database connection function
def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(
            host=st.secrets["SUPABASE"]["HOST"],
            database=st.secrets["SUPABASE"]["DATABASE"],
            user=st.secrets["SUPABASE"]["USER"],
            password=st.secrets["SUPABASE"]["PASSWORD"],
            port=st.secrets["SUPABASE"]["PORT"],
            # Force IPv4 connection to avoid IPv6 issues
            options='-c family=ipv4'
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

# Initialize database table
def init_database():
    """Initialize the database table if it doesn't exist"""
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS time_entries (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    employee TEXT NOT NULL,
                    clock_in TIMESTAMPTZ NOT NULL,
                    clock_out TIMESTAMPTZ,
                    pay_rate_type TEXT DEFAULT 'Standard',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            # Check if pay_rate_type column exists, add if not
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'time_entries' 
                AND column_name = 'pay_rate_type'
            """)
            
            if not cursor.fetchone():
                cursor.execute("""
                    ALTER TABLE time_entries 
                    ADD COLUMN pay_rate_type TEXT DEFAULT 'Standard'
                """)
                st.success("✅ Database updated with pay rate functionality")
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"Database initialization failed: {e}")

# Database operations
def clock_in(employee_name, is_supervisor=False):
    """Clock in an employee"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Check if employee already has an open shift
        cursor.execute("""
            SELECT id FROM time_entries 
            WHERE employee = %s AND clock_out IS NULL
        """, (employee_name,))
        
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False, f"{employee_name} already has an open shift"
        
        # Determine pay rate type
        current_time = datetime.now(timezone.utc)
        pay_rate_type = determine_pay_rate_type(is_supervisor, current_time)
        
        # Insert new clock-in record
        cursor.execute("""
            INSERT INTO time_entries (employee, clock_in, pay_rate_type)
            VALUES (%s, NOW(), %s)
        """, (employee_name, pay_rate_type))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        rate_message = f" ({pay_rate_type} Rate)"
        return True, f"{employee_name} clocked in successfully{rate_message}"
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return False, f"Error clocking in: {e}"

def clock_out(employee_name):
    """Clock out an employee"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Find the most recent open shift for this employee
        cursor.execute("""
            SELECT id FROM time_entries 
            WHERE employee = %s AND clock_out IS NULL
            ORDER BY clock_in DESC
            LIMIT 1
        """, (employee_name,))
        
        open_shift = cursor.fetchone()
        if not open_shift:
            cursor.close()
            conn.close()
            return False, f"No open shift found for {employee_name}"
        
        # Update the clock_out time
        cursor.execute("""
            UPDATE time_entries 
            SET clock_out = NOW()
            WHERE id = %s
        """, (open_shift[0],))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True, f"{employee_name} clocked out successfully"
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return False, f"Error clocking out: {e}"

def get_employee_timesheet(employee_name):
    """Get timesheet for a specific employee"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, clock_in, clock_out, pay_rate_type, created_at
            FROM time_entries 
            WHERE employee = %s
            ORDER BY clock_in DESC
        """, (employee_name,))
        
        entries = cursor.fetchall()
        cursor.close()
        conn.close()
        return entries
        
    except Exception as e:
        cursor.close()
        conn.close()
        st.error(f"Error fetching timesheet: {e}")
        return []

def get_all_timesheets():
    """Get all timesheet entries for manager view"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, employee, clock_in, clock_out, pay_rate_type, created_at
            FROM time_entries 
            ORDER BY clock_in DESC
        """)
        
        entries = cursor.fetchall()
        cursor.close()
        conn.close()
        return entries
        
    except Exception as e:
        cursor.close()
        conn.close()
        st.error(f"Error fetching all timesheets: {e}")
        return []

def delete_entry(entry_id):
    """Delete a time entry"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM time_entries WHERE id = %s", (entry_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return True, "Entry deleted successfully"
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return False, f"Error deleting entry: {e}"

def determine_pay_rate_type(is_supervisor, clock_in_time=None):
    """Determine the pay rate type based on time and supervisor status"""
    if is_supervisor:
        return "Supervisor"
    
    if clock_in_time is None:
        clock_in_time = datetime.now(timezone.utc)
    
    # Check if it's enhanced hours in BST
    if is_bst_enhanced_hours(clock_in_time):
        return "Enhanced"
    else:
        return "Standard"

def add_shift_manually(employee_name, clock_in_date, clock_in_time, clock_out_date, clock_out_time, is_supervisor, pay_rate_override=None):
    """Add a shift manually for managers"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Combine date and time for clock-in
        clock_in_datetime = datetime.combine(clock_in_date, clock_in_time)
        clock_in_datetime = clock_in_datetime - timedelta(hours=1)
        
        # Combine date and time for clock-out (if provided)
        clock_out_datetime = None
        if clock_out_date and clock_out_time:
            clock_out_datetime = datetime.combine(clock_out_date, clock_out_time)
            clock_out_datetime = clock_out_datetime - timedelta(hours=1)
        
        # Determine pay rate type
        if pay_rate_override:
            pay_rate_type = pay_rate_override
        else:
            pay_rate_type = determine_pay_rate_type(is_supervisor, clock_in_datetime)
        
        # Insert new shift record
        cursor.execute("""
            INSERT INTO time_entries (employee, clock_in, clock_out, pay_rate_type)
            VALUES (%s, %s, %s, %s)
        """, (employee_name, clock_in_datetime, clock_out_datetime, pay_rate_type))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, f"Shift added for {employee_name} ({pay_rate_type} Rate)"
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return False, f"Error adding shift: {e}"

def edit_shift(entry_id, employee_name, clock_in_date, clock_in_time, clock_out_date, clock_out_time, is_supervisor, pay_rate_override=None):
    """Edit an existing shift"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        cursor = conn.cursor()
        
        # Combine date and time for clock-in
        clock_in_datetime = datetime.combine(clock_in_date, clock_in_time)
        clock_in_datetime = clock_in_datetime - timedelta(hours=1)
        
        # Combine date and time for clock-out (if provided)
        clock_out_datetime = None
        if clock_out_date and clock_out_time:
            clock_out_datetime = datetime.combine(clock_out_date, clock_out_time)
            clock_out_datetime = clock_out_datetime - timedelta(hours=1)
        
        # Determine pay rate type
        if pay_rate_override:
            pay_rate_type = pay_rate_override
        else:
            pay_rate_type = determine_pay_rate_type(is_supervisor, clock_in_datetime)
        
        # Update the shift record
        cursor.execute("""
            UPDATE time_entries 
            SET employee = %s, clock_in = %s, clock_out = %s, pay_rate_type = %s
            WHERE id = %s
        """, (employee_name, clock_in_datetime, clock_out_datetime, pay_rate_type, entry_id))
        
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return False, "Shift not found"
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True, f"Shift updated for {employee_name} ({pay_rate_type} Rate)"
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        return False, f"Error updating shift: {e}"

def get_shift_by_id(entry_id):
    """Get a specific shift by ID"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, employee, clock_in, clock_out, pay_rate_type, created_at
            FROM time_entries 
            WHERE id = %s
        """, (entry_id,))
        
        entry = cursor.fetchone()
        cursor.close()
        conn.close()
        return entry
        
    except Exception as e:
        cursor.close()
        conn.close()
        st.error(f"Error fetching shift: {e}")
        return None

# Initialize database on app start
init_database()

# Main app
def main():
    st.title("🕒 The Tythe Barn - Time Tracker")
    st.markdown("---")
    
    # Pay rate information
    with st.expander("💰 Pay Rate Information", expanded=False):
        st.markdown("""
        **Pay Rate Rules:**
        - **Standard Rate:** Regular hours (4:00 AM - 7:00 PM)
        - **Enhanced Rate:** Night hours (7:00 PM - 4:00 AM) 
        - **Supervisor Rate:** When supervisor role is selected (overrides other rates)
        
        **Note:** If you clock in during enhanced hours AND select supervisor role, you'll receive the supervisor rate.
        """)
    
    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Choose a page:",
        ["Employee Clock In/Out", "Personal Timesheet", "Export Timesheet", "Manager Dashboard"]
    )
    
    if page == "Employee Clock In/Out":
        show_employee_interface()
    elif page == "Personal Timesheet":
        show_personal_timesheet()
    elif page == "Export Timesheet":
        show_export_interface()
    elif page == "Manager Dashboard":
        show_manager_dashboard()

def show_employee_interface():
    """Employee clock in/out interface"""
    st.header("👤 Employee Clock In/Out")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Clock In/Out")
        employee_name = st.text_input("Enter your full name:", key="employee_name")
        
        if employee_name.strip():
            # Add supervisor tick box
            is_supervisor = st.checkbox("👑 Supervisor Role", key="supervisor_checkbox")
            
            col_in, col_out = st.columns(2)
            
            with col_in:
                if st.button("🟢 Clock In", type="primary", use_container_width=True):
                    success, message = clock_in(employee_name.strip(), is_supervisor)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            
            with col_out:
                if st.button("🔴 Clock Out", type="secondary", use_container_width=True):
                    success, message = clock_out(employee_name.strip())
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        else:
            st.info("Please enter your name to clock in or out")
    
    with col2:
        st.subheader("Quick Status")
        if 'employee_name' in st.session_state and st.session_state.employee_name.strip():
            name = st.session_state.employee_name.strip()
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT clock_in, pay_rate_type FROM time_entries 
                    WHERE employee = %s AND clock_out IS NULL
                    ORDER BY clock_in DESC
                    LIMIT 1
                """, (name,))
                
                open_shift = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if open_shift:
                    clock_in_time, pay_rate_type = open_shift
                    st.success(f"✅ {name} is currently clocked in")
                    st.info(f"Clocked in at: {clock_in_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.info(f"Pay Rate: {pay_rate_type}")
                else:
                    st.info(f"ℹ️ {name} is not currently clocked in")

def show_personal_timesheet():
    """Personal timesheet view"""
    st.header("📊 Personal Timesheet")
    
    employee_name = st.text_input("Enter your full name to view timesheet:", key="timesheet_name")
    
    if employee_name.strip():
        entries = get_employee_timesheet(employee_name.strip())
        
        if entries:
            st.subheader(f"Timesheet for {employee_name.strip()}")
            
            # Prepare data for display
            timesheet_data = []
            for entry in entries:
                entry_id, clock_in, clock_out, pay_rate_type, created_at = entry
                
                # Calculate the actual split using our new logic
                is_supervisor = (pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
                
                # Create a display string showing the split
                if is_supervisor:
                    rate_display = f"Supervisor ({split['Supervisor']}h)"
                elif split['Standard'] > 0 and split['Enhanced'] > 0:
                    rate_display = f"Mixed: {split['Standard']}h Standard, {split['Enhanced']}h Enhanced"
                elif split['Enhanced'] > 0:
                    rate_display = f"Enhanced ({split['Enhanced']}h)"
                else:
                    rate_display = f"Standard ({split['Standard']}h)"
                
                timesheet_data.append({
                    "Date": clock_in.strftime('%Y-%m-%d'),
                    "Clock-In": clock_in.strftime('%H:%M:%S'),
                    "Clock-Out": clock_out.strftime('%H:%M:%S') if clock_out else "🟢 Still Open",
                    "Duration": str(clock_out - clock_in).split('.')[0] if clock_out else "In Progress",
                    "Pay Rate": rate_display
                })
            
            st.dataframe(timesheet_data, use_container_width=True)
        else:
            st.info(f"No time entries found for {employee_name.strip()}")
    else:
        st.info("Please enter your name to view your timesheet")

def show_export_interface():
    """Export timesheet interface for both employees and managers"""
    st.header("📤 Export Timesheet")
    
    # Check if user is manager
    is_manager = st.session_state.get('manager_authenticated', False)
    
    if is_manager:
        st.success("👨‍💼 Manager Export Access")
        st.info("You can export timesheets for any employee or the entire team.")
    else:
        st.info("👤 Employee Export Access")
        st.info("You can only export your own timesheet.")
    
    st.markdown("---")
    
    # Employee selection (managers only)
    employee_name = None
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
                employee_name = st.text_input("Employee Name:", key="export_employee_name")
            else:
                st.info("📊 Bulk export will include all staff members")
    else:
        employee_name = st.text_input("Enter your name:", key="export_employee_name")
    
    st.markdown("---")
    
    # Date range selection
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
                    return
                st.info(f"Custom Range: {start_date} to {end_date}")
            else:
                st.warning("Please select both start and end dates")
        else:
            start_date, end_date = get_date_range(date_option)
            st.info(f"Selected: {start_date} to {end_date}")
    
    st.markdown("---")
    
    # Export format and options
    st.subheader("📋 Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        export_format = st.selectbox(
            "Export Format:",
            ["Excel (.xlsx)", "PDF"],
            key="export_format"
        )
    
    with col2:
        if is_manager:
            role_filter = st.selectbox(
                "Filter by Role:",
                ["All Roles", "Staff Only", "Supervisors Only"],
                key="role_filter"
            )
        else:
            role_filter = "All Roles"
    
    st.markdown("---")
    
    # Preview and export
    if st.button("👁️ Preview Data", type="secondary"):
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
                        detailed_data.append({
                            "Employee": emp,
                            "Date": clock_in.strftime('%Y-%m-%d'),
                            "Clock-In": clock_in.strftime('%H:%M:%S'),
                            "Clock-Out": clock_out.strftime('%H:%M:%S') if clock_out else "In Progress",
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
            
            # Export buttons
            st.markdown("---")
            st.subheader("📤 Export")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if export_format == "Excel (.xlsx)":
                    if st.button("📊 Export to Excel", type="primary"):
                        filename = f"timesheet_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                        export_to_excel(entries, filename)
                        
                        # Create download link
                        with open(filename, "rb") as f:
                            st.download_button(
                                label="📥 Download Excel File",
                                data=f.read(),
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        os.remove(filename)  # Clean up
                else:
                    if st.button("📄 Export to PDF", type="primary"):
                        filename = f"timesheet_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                        export_to_pdf(entries, filename)
                        
                        # Create download link
                        with open(filename, "rb") as f:
                            st.download_button(
                                label="📥 Download PDF File",
                                data=f.read(),
                                file_name=filename,
                                mime="application/pdf"
                            )
                        os.remove(filename)  # Clean up
            
            with col2:
                st.info("💡 **Export includes:**\n- Staff name & role\n- Clock-in/out times\n- Total hours worked\n- Applied pay rate\n- Supervisor flag\n- Summary totals")
        else:
            st.warning("No entries found for the selected criteria")
    
    # Direct export without preview
    st.markdown("---")
    if st.button("🚀 Export Directly", type="primary"):
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
            if export_format == "Excel (.xlsx)":
                filename = f"timesheet_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                export_to_excel(entries, filename)
                
                with open(filename, "rb") as f:
                    st.download_button(
                        label="📥 Download Excel File",
                        data=f.read(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                os.remove(filename)
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
                os.remove(filename)
        else:
            st.warning("No entries found for the selected criteria")

def show_manager_dashboard():
    """Manager dashboard with password protection"""
    st.header("👨‍💼 Manager Dashboard")
    
    # Password protection
    if 'manager_authenticated' not in st.session_state:
        st.session_state.manager_authenticated = False
    
    if not st.session_state.manager_authenticated:
        password = st.text_input("Enter manager password:", type="password")
        if st.button("Login"):
            # Simple password check - in production, use proper authentication
            if password == st.secrets["MANAGER_PASSWORD"]:
                st.session_state.manager_authenticated = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Incorrect password")
        return
    
    # Manager is authenticated
    st.success("✅ Manager access granted")
    
    if st.button("Logout"):
        st.session_state.manager_authenticated = False
        st.rerun()
    
    # Manager controls tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📊 View All Entries", "➕ Add Shift", "✏️ Edit Shift", "🗑️ Delete Entry"])
    
    with tab1:
        st.subheader("All Time Entries")
        entries = get_all_timesheets()
        
        if entries:
            # Quick export section
            with st.expander("📤 Quick Export", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    quick_export_format = st.selectbox("Format:", ["Excel (.xlsx)", "PDF"], key="quick_export_format")
                with col2:
                    if quick_export_format == "Excel (.xlsx)":
                        if st.button("📊 Export All to Excel", key="quick_excel"):
                            filename = f"all_timesheets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                            export_to_excel(entries, filename)
                            with open(filename, "rb") as f:
                                st.download_button(
                                    label="📥 Download Excel File",
                                    data=f.read(),
                                    file_name=filename,
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )
                            os.remove(filename)
                    else:
                        if st.button("📄 Export All to PDF", key="quick_pdf"):
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
            
            # Prepare data for display
            all_data = []
            for entry in entries:
                entry_id, employee, clock_in, clock_out, pay_rate_type, created_at = entry
                
                # Calculate the actual split using our new logic
                is_supervisor = (pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
                
                # Create a display string showing the split
                if is_supervisor:
                    rate_display = f"Supervisor ({split['Supervisor']}h)"
                elif split['Standard'] > 0 and split['Enhanced'] > 0:
                    rate_display = f"Mixed: {split['Standard']}h Standard, {split['Enhanced']}h Enhanced"
                elif split['Enhanced'] > 0:
                    rate_display = f"Enhanced ({split['Enhanced']}h)"
                else:
                    rate_display = f"Standard ({split['Standard']}h)"
                
                all_data.append({
                    "Employee": employee,
                    "Date": clock_in.strftime('%Y-%m-%d'),
                    "Clock-In": clock_in.strftime('%H:%M:%S'),
                    "Clock-Out": clock_out.strftime('%H:%M:%S') if clock_out else "🟢 Still Open",
                    "Duration": str(clock_out - clock_in).split('.')[0] if clock_out else "In Progress",
                    "Pay Rate": rate_display,
                    "Entry ID": str(entry_id)
                })
            
            # Display the data
            st.dataframe(all_data, use_container_width=True)
        else:
            st.info("No time entries found")
    
    with tab2:
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
                success, message = add_shift_manually(
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
    
    with tab3:
        st.subheader("✏️ Edit Shift")
        
        # Show instructions first
        st.info("💡 **Instructions:** Copy an Entry ID from the 'View All Entries' tab above, then paste it here to edit that shift.")
        
        # Get shift to edit
        entry_id = st.text_input("Enter Entry ID to edit:", key="edit_entry_id", placeholder="Paste Entry ID here...")
        
        if not entry_id:
            st.warning("Please enter an Entry ID to edit a shift")
        else:
            shift = get_shift_by_id(entry_id)
            if shift:
                entry_id, employee, clock_in, clock_out, pay_rate_type, created_at = shift
                
                st.success(f"✅ Found shift for {employee}")
                
                # Debug info (can be removed later)
                with st.expander("🔍 Debug Info", expanded=False):
                    st.write(f"Entry ID: {entry_id}")
                    st.write(f"Employee: {employee}")
                    st.write(f"Clock In: {clock_in}")
                    st.write(f"Clock Out: {clock_out}")
                    st.write(f"Pay Rate: {pay_rate_type}")
                
                st.markdown("---")
                st.subheader("Edit Shift Details")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    employee_name = st.text_input("Employee Name:", value=employee, key="edit_employee")
                    clock_in_date = st.date_input("Clock-In Date:", value=clock_in.date(), key="edit_clock_in_date")
                    clock_in_time = st.time_input("Clock-In Time:", value=clock_in.time(), key="edit_clock_in_time")
                    is_supervisor = st.checkbox("👑 Supervisor Role", value=pay_rate_type=="Supervisor", key="edit_supervisor")
                
                with col2:
                    # Handle None clock_out values properly
                    if clock_out:
                        default_clock_out_date = clock_out.date()
                        default_clock_out_time = clock_out.time()
                    else:
                        default_clock_out_date = None
                        default_clock_out_time = None
                    
                    clock_out_date = st.date_input("Clock-Out Date (optional):", value=default_clock_out_date, key="edit_clock_out_date")
                    clock_out_time = st.time_input("Clock-Out Time (optional):", value=default_clock_out_time, key="edit_clock_out_time")
                    
                    pay_rate_override = st.selectbox(
                        "Pay Rate Override:",
                        ["Auto-calculate", "Standard", "Enhanced", "Supervisor"],
                        index=["Auto-calculate", "Standard", "Enhanced", "Supervisor"].index(pay_rate_type) if pay_rate_type in ["Standard", "Enhanced", "Supervisor"] else 0,
                        key="edit_pay_rate_override"
                    )
                    
                    if pay_rate_override == "Auto-calculate":
                        pay_rate_override = None
                
                if st.button("✏️ Update Shift", type="primary"):
                    if employee_name.strip():
                        success, message = edit_shift(
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
            else:
                st.error("❌ Shift not found. Please check the Entry ID.")
                st.info("💡 Make sure you copied the Entry ID correctly from the 'View All Entries' tab.")
    
    with tab4:
        st.subheader("🗑️ Delete Entry")
        entry_to_delete = st.text_input("Enter Entry ID to delete:", key="delete_entry_id")
        if st.button("🗑️ Delete Entry", type="secondary"):
            if entry_to_delete:
                success, message = delete_entry(entry_to_delete)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please enter an Entry ID")

if __name__ == "__main__":
    main() 