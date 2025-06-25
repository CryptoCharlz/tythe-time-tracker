import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone, time as dtime
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
        return 0  # Return 0 for in-progress shifts
    
    duration = clock_out - clock_in
    hours = duration.total_seconds() / 3600
    return round(hours, 2)

def get_bst_time(utc_time):
    return utc_time + timedelta(hours=1)

def is_bst_enhanced_hours(dt):
    # dt should be BST
    hour = dt.hour
    return hour >= 19 or hour < 4

def split_shift_by_rate(clock_in, clock_out, is_supervisor):
    """
    Returns a dict: {'Standard': hours, 'Enhanced': hours, 'Supervisor': hours}
    All times are assumed to be UTC and will be converted to BST for rate logic.
    Splits at 19:00 (7PM) and 04:00 (4AM) BST boundaries.
    """
    if not clock_out:
        return {'Standard': 0, 'Enhanced': 0, 'Supervisor': 0}
    if is_supervisor:
        total = (clock_out - clock_in).total_seconds() / 3600
        return {'Standard': 0, 'Enhanced': 0, 'Supervisor': round(total, 2)}
    # Convert to BST
    bst_in = get_bst_time(clock_in)
    bst_out = get_bst_time(clock_out)
    # Boundaries
    day = bst_in.date()
    seven_pm = datetime.combine(day, dtime(19, 0)).replace(tzinfo=None)
    four_am_next = datetime.combine(day + timedelta(days=1), dtime(4, 0)).replace(tzinfo=None)
    # If shift ends before 7PM
    if bst_out <= seven_pm:
        std = (bst_out - bst_in).total_seconds() / 3600
        return {'Standard': round(std, 2), 'Enhanced': 0, 'Supervisor': 0}
    # If shift starts after 7PM and before 4AM
    if bst_in >= seven_pm and bst_in < four_am_next:
        enh = (min(bst_out, four_am_next) - bst_in).total_seconds() / 3600
        std = max((bst_out - four_am_next).total_seconds() / 3600, 0) if bst_out > four_am_next else 0
        return {'Standard': round(std, 2), 'Enhanced': round(enh, 2), 'Supervisor': 0}
    # If shift starts before 7PM and ends after 7PM
    std = (seven_pm - bst_in).total_seconds() / 3600 if bst_in < seven_pm else 0
    enh = (min(bst_out, four_am_next) - max(bst_in, seven_pm)).total_seconds() / 3600 if bst_out > seven_pm else 0
    std2 = (bst_out - four_am_next).total_seconds() / 3600 if bst_out > four_am_next else 0
    return {
        'Standard': round(std + max(std2, 0), 2),
        'Enhanced': round(max(enh, 0), 2),
        'Supervisor': 0
    }

def calculate_staff_summary(entries):
    """Calculate summary by staff member with hours per pay rate type"""
    staff_summary = {}
    
    for entry in entries:
        entry_id, employee, clock_in, clock_out, pay_rate_type, created_at = entry
        is_supervisor = (pay_rate_type == 'Supervisor')
        split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
        
        if employee not in staff_summary:
            staff_summary[employee] = {
                'Standard': 0,
                'Enhanced': 0,
                'Supervisor': 0,
                'total_hours': 0,
                'total_shifts': 0
            }
        
        # Add hours to the appropriate pay rate type
        staff_summary[employee]['Standard'] += split['Standard']
        staff_summary[employee]['Enhanced'] += split['Enhanced']
        staff_summary[employee]['Supervisor'] += split['Supervisor']
        staff_summary[employee]['total_hours'] += sum(split.values())
        staff_summary[employee]['total_shifts'] += 1
    
    return staff_summary

def calculate_summary(entries):
    """Calculate overall summary statistics"""
    staff_summary = calculate_staff_summary(entries)
    
    total_hours = sum(staff['total_hours'] for staff in staff_summary.values())
    total_shifts = sum(staff['total_shifts'] for staff in staff_summary.values())
    unique_employees = len(staff_summary)
    
    return {
        'total_hours': round(total_hours, 2),
        'total_shifts': total_shifts,
        'unique_employees': unique_employees,
        'staff_summary': staff_summary
    }

def export_to_excel(entries, filename="timesheet_export.xlsx"):
    """Export timesheet data to Excel with staff summaries"""
    if not entries:
        return None
    
    # Calculate staff summary
    staff_summary = calculate_staff_summary(entries)
    
    # Prepare staff summary data for Excel
    summary_data = []
    for employee, data in staff_summary.items():
        summary_data.append({
            'Staff Name': employee,
            'Standard Hours': data['Standard'],
            'Enhanced Hours': data['Enhanced'],
            'Supervisor Hours': data['Supervisor'],
            'Total Hours': data['total_hours'],
            'Total Shifts': data['total_shifts']
        })
    
    # Create DataFrame
    df_summary = pd.DataFrame(summary_data)
    
    # Also prepare detailed data for second sheet
    detailed_data = []
    for entry in entries:
        entry_id, employee, clock_in, clock_out, pay_rate_type, created_at = entry
        is_supervisor = (pay_rate_type == 'Supervisor')
        split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
        detailed_data.append({
            'Staff Name': employee,
            'Date': clock_in.strftime('%Y-%m-%d'),
            'Clock-In': clock_in.strftime('%H:%M:%S'),
            'Clock-Out': clock_out.strftime('%H:%M:%S') if clock_out else 'In Progress',
            'Standard Hours': split['Standard'],
            'Enhanced Hours': split['Enhanced'],
            'Supervisor Hours': split['Supervisor'],
            'Total Hours': sum(split.values()),
            'Pay Rate Type': pay_rate_type,
            'Supervisor Flag': 'Yes' if pay_rate_type == "Supervisor" else 'No'
        })
    
    df_detailed = pd.DataFrame(detailed_data)
    
    # Calculate overall summary
    overall_summary = calculate_summary(entries)
    
    # Create Excel file with multiple sheets
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Staff Summary sheet (main sheet)
        df_summary.to_excel(writer, sheet_name='Staff Summary', index=False)
        
        # Detailed timesheet data
        df_detailed.to_excel(writer, sheet_name='Detailed Shifts', index=False)
        
        # Overall summary sheet
        summary_data = {
            'Metric': ['Total Hours', 'Total Shifts', 'Unique Employees'],
            'Value': [overall_summary['total_hours'], overall_summary['total_shifts'], overall_summary['unique_employees']]
        }
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Overall Summary', index=False)
    
    return filename

def export_to_pdf(entries, filename="timesheet_export.pdf"):
    """Export timesheet data to PDF with staff summaries"""
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
    title = Paragraph("The Tythe Barn - Staff Hours Summary", title_style)
    story.append(title)
    story.append(Spacer(1, 20))
    
    # Calculate summaries
    staff_summary = calculate_staff_summary(entries)
    overall_summary = calculate_summary(entries)
    
    # Overall summary section
    summary_text = f"""
    <b>Overall Summary:</b><br/>
    Total Hours: {overall_summary['total_hours']}<br/>
    Total Shifts: {overall_summary['total_shifts']}<br/>
    Unique Employees: {overall_summary['unique_employees']}
    """
    summary_para = Paragraph(summary_text, styles['Normal'])
    story.append(summary_para)
    story.append(Spacer(1, 20))
    
    # Staff summary table
    story.append(Paragraph("<b>Staff Hours by Pay Rate Type:</b>", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    # Prepare table data
    table_data = [['Staff Name', 'Standard Hours', 'Enhanced Hours', 'Supervisor Hours', 'Total Hours', 'Total Shifts']]
    
    for employee, data in staff_summary.items():
        row = [
            employee,
            str(data['Standard']),
            str(data['Enhanced']),
            str(data['Supervisor']),
            str(data['total_hours']),
            str(data['total_shifts'])
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