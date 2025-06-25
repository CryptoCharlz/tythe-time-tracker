import streamlit as st
import psycopg2
import os
from datetime import datetime
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
        pay_rate_type = determine_pay_rate_type(is_supervisor)
        
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
        clock_in_time = datetime.now()
    
    hour = clock_in_time.hour
    
    # Enhanced rate: 7:00 PM (19:00) to 4:00 AM (04:00)
    if hour >= 19 or hour < 4:
        return "Enhanced"
    else:
        return "Standard"

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
        ["Employee Clock In/Out", "Personal Timesheet", "Manager Dashboard"]
    )
    
    if page == "Employee Clock In/Out":
        show_employee_interface()
    elif page == "Personal Timesheet":
        show_personal_timesheet()
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
                timesheet_data.append({
                    "Date": clock_in.strftime('%Y-%m-%d'),
                    "Clock-In": clock_in.strftime('%H:%M:%S'),
                    "Clock-Out": clock_out.strftime('%H:%M:%S') if clock_out else "🟢 Still Open",
                    "Duration": str(clock_out - clock_in).split('.')[0] if clock_out else "In Progress",
                    "Pay Rate Type": pay_rate_type
                })
            
            st.dataframe(timesheet_data, use_container_width=True)
        else:
            st.info(f"No time entries found for {employee_name.strip()}")
    else:
        st.info("Please enter your name to view your timesheet")

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
    
    st.subheader("All Time Entries")
    
    entries = get_all_timesheets()
    
    if entries:
        # Prepare data for display
        all_data = []
        for entry in entries:
            entry_id, employee, clock_in, clock_out, pay_rate_type, created_at = entry
            all_data.append({
                "Employee": employee,
                "Date": clock_in.strftime('%Y-%m-%d'),
                "Clock-In": clock_in.strftime('%H:%M:%S'),
                "Clock-Out": clock_out.strftime('%H:%M:%S') if clock_out else "🟢 Still Open",
                "Duration": str(clock_out - clock_in).split('.')[0] if clock_out else "In Progress",
                "Pay Rate Type": pay_rate_type,
                "Entry ID": str(entry_id)
            })
        
        # Display the data
        st.dataframe(all_data, use_container_width=True)
        
        # Delete functionality
        st.subheader("Delete Entry")
        entry_to_delete = st.text_input("Enter Entry ID to delete:")
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
    else:
        st.info("No time entries found")

if __name__ == "__main__":
    main() 