import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import base64

def get_date_range(option):
    """Get date range based on selection"""
    today = datetime.now().date()
    
    if option == "This Week":
        # Monday to Sunday
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif option == "Last Week":
        # Previous Monday to Sunday
        start = today - timedelta(days=today.weekday() + 7)
        end = start + timedelta(days=6)
    elif option == "This Month":
        # First to last day of current month
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    else:  # Custom range
        return None, None
    
    return start, end

def get_timesheet_data(employee_name=None, start_date=None, end_date=None, is_manager=False):
    """Get timesheet data with filters"""
    conn = st.secrets.get("SUPABASE", {})
    if not conn:
        return []
    
    try:
        import psycopg2
        db_conn = psycopg2.connect(
            host=st.secrets["SUPABASE"]["HOST"],
            database=st.secrets["SUPABASE"]["DATABASE"],
            user=st.secrets["SUPABASE"]["USER"],
            password=st.secrets["SUPABASE"]["PASSWORD"],
            port=st.secrets["SUPABASE"]["PORT"],
            options='-c family=ipv4'
        )
        
        cursor = db_conn.cursor()
        
        # Build query based on filters
        query = """
            SELECT id, employee, clock_in, clock_out, pay_rate_type, created_at
            FROM time_entries 
            WHERE 1=1
        """
        params = []
        
        if employee_name and not is_manager:
            query += " AND employee = %s"
            params.append(employee_name)
        
        if start_date:
            query += " AND DATE(clock_in) >= %s"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(clock_in) <= %s"
            params.append(end_date)
        
        query += " ORDER BY employee, clock_in DESC"
        
        cursor.execute(query, params)
        entries = cursor.fetchall()
        
        cursor.close()
        db_conn.close()
        
        return entries
        
    except Exception as e:
        st.error(f"Database error: {e}")
        return []

def calculate_hours(clock_in, clock_out):
    """Calculate hours worked"""
    if not clock_out:
        return "In Progress"
    
    duration = clock_out - clock_in
    hours = duration.total_seconds() / 3600
    return round(hours, 2)

def calculate_summary(entries):
    """Calculate summary statistics"""
    total_hours = 0
    total_shifts = 0
    employees = set()
    
    for entry in entries:
        _, employee, clock_in, clock_out, pay_rate_type, _ = entry
        employees.add(employee)
        total_shifts += 1
        
        if clock_out:
            hours = calculate_hours(clock_in, clock_out)
            if isinstance(hours, (int, float)):
                total_hours += hours
    
    return {
        'total_hours': round(total_hours, 2),
        'total_shifts': total_shifts,
        'unique_employees': len(employees)
    }

def export_to_excel(entries, filename="timesheet_export.xlsx"):
    """Export timesheet data to Excel"""
    if not entries:
        return None
    
    # Prepare data for Excel
    data = []
    for entry in entries:
        entry_id, employee, clock_in, clock_out, pay_rate_type, created_at = entry
        hours = calculate_hours(clock_in, clock_out)
        is_supervisor = pay_rate_type == "Supervisor"
        
        data.append({
            'Staff Name': employee,
            'Role': 'Supervisor' if is_supervisor else 'Staff',
            'Date': clock_in.strftime('%Y-%m-%d'),
            'Clock-In': clock_in.strftime('%H:%M:%S'),
            'Clock-Out': clock_out.strftime('%H:%M:%S') if clock_out else 'In Progress',
            'Hours Worked': hours,
            'Pay Rate': pay_rate_type,
            'Supervisor Flag': 'Yes' if is_supervisor else 'No'
        })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Calculate summary
    summary = calculate_summary(entries)
    
    # Create Excel file with multiple sheets
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Main timesheet data
        df.to_excel(writer, sheet_name='Timesheet', index=False)
        
        # Summary sheet
        summary_data = {
            'Metric': ['Total Hours', 'Total Shifts', 'Unique Employees'],
            'Value': [summary['total_hours'], summary['total_shifts'], summary['unique_employees']]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    return filename

def export_to_pdf(entries, filename="timesheet_export.pdf"):
    """Export timesheet data to PDF"""
    if not entries:
        return None
    
    # Create PDF document
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    title = Paragraph("The Tythe Barn - Timesheet Report", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Summary section
    summary = calculate_summary(entries)
    summary_text = f"""
    <b>Summary:</b><br/>
    Total Hours: {summary['total_hours']}<br/>
    Total Shifts: {summary['total_shifts']}<br/>
    Unique Employees: {summary['unique_employees']}
    """
    summary_para = Paragraph(summary_text, styles['Normal'])
    story.append(summary_para)
    story.append(Spacer(1, 20))
    
    # Prepare table data
    table_data = [['Staff Name', 'Role', 'Date', 'Clock-In', 'Clock-Out', 'Hours', 'Pay Rate', 'Supervisor']]
    
    for entry in entries:
        entry_id, employee, clock_in, clock_out, pay_rate_type, created_at = entry
        hours = calculate_hours(clock_in, clock_out)
        is_supervisor = pay_rate_type == "Supervisor"
        
        row = [
            employee,
            'Supervisor' if is_supervisor else 'Staff',
            clock_in.strftime('%Y-%m-%d'),
            clock_in.strftime('%H:%M:%S'),
            clock_out.strftime('%H:%M:%S') if clock_out else 'In Progress',
            str(hours),
            pay_rate_type,
            'Yes' if is_supervisor else 'No'
        ]
        table_data.append(row)
    
    # Create table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    
    story.append(table)
    
    # Build PDF
    doc.build(story)
    return filename

def get_download_link(file_path, file_name, file_type):
    """Create download link for files"""
    with open(file_path, "rb") as f:
        data = f.read()
    
    b64 = base64.b64encode(data).decode()
    href = f'<a href="data:application/{file_type};base64,{b64}" download="{file_name}">Download {file_name}</a>'
    return href 