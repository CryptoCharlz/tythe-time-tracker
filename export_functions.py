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
    Handles overnight shifts correctly.
    """
    if not clock_out:
        return {'Standard': 0, 'Enhanced': 0, 'Supervisor': 0}
    if is_supervisor:
        total = (clock_out - clock_in).total_seconds() / 3600
        return {'Standard': 0, 'Enhanced': 0, 'Supervisor': round(total, 2)}
    # Convert to BST and make naive for comparison
    bst_in = get_bst_time(clock_in).replace(tzinfo=None)
    bst_out = get_bst_time(clock_out).replace(tzinfo=None)
    if bst_out <= bst_in:
        return {'Standard': 0, 'Enhanced': 0, 'Supervisor': 0}
    
    # Enhanced window: 19:00 BST to 04:00 BST next day
    # Always ends at 4:00 BST on the day after the shift starts
    if bst_in.hour < 4:
        # Shift starts in early morning, enhanced window is 19:00 previous day to 04:00 current day
        enhanced_start = datetime.combine(bst_in.date() - timedelta(days=1), dtime(19, 0))
        enhanced_end = datetime.combine(bst_in.date(), dtime(4, 0))
    else:
        # Shift starts after 4 AM, enhanced window is 19:00 current day to 04:00 next day
        enhanced_start = datetime.combine(bst_in.date(), dtime(19, 0))
        enhanced_end = datetime.combine(bst_in.date() + timedelta(days=1), dtime(4, 0))
    
    # Calculate overlap with enhanced window
    enh_start = max(bst_in, enhanced_start)
    enh_end = min(bst_out, enhanced_end)
    enhanced_hours = max((enh_end - enh_start).total_seconds() / 3600, 0) if enh_start < enh_end else 0
    # Standard: the rest
    total_hours = (bst_out - bst_in).total_seconds() / 3600
    standard_hours = total_hours - enhanced_hours
    return {
        'Standard': round(standard_hours, 2),
        'Enhanced': round(enhanced_hours, 2),
        'Supervisor': 0
    }

def calculate_staff_summary(entries):
    """Calculate summary by staff member with hours per pay rate type"""
    staff_summary = {}
    
    for entry in entries:
        # Handle both TimeEntry objects and tuples for backward compatibility
        if hasattr(entry, 'employee'):
            # TimeEntry object
            employee = entry.employee
            clock_in = entry.clock_in
            clock_out = entry.clock_out
            pay_rate_type = entry.pay_rate_type.value if hasattr(entry.pay_rate_type, 'value') else entry.pay_rate_type
        else:
            # Tuple format (backward compatibility)
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

def export_to_excel(entries, filename="timesheet_export.xlsx", start_date=None, end_date=None):
    """Export timesheet data to Excel with staff summaries and individual shifts"""
    if not entries:
        return None
    
    # Calculate staff summary
    staff_summary = calculate_staff_summary(entries)
    
    # Sort entries by employee (case-insensitive, trimmed) and clock_in
    # Handle both TimeEntry objects and tuples for backward compatibility
    if entries and hasattr(entries[0], 'employee'):
        # TimeEntry objects
        entries_sorted = sorted(entries, key=lambda e: (e.employee.strip().lower(), e.clock_in))
    else:
        # Tuple format (backward compatibility)
        entries_sorted = sorted(entries, key=lambda e: (e[1].strip().lower(), e[2]))
    
    # Prepare hierarchical data for Excel
    hierarchical_data = []
    
    for employee, data in staff_summary.items():
        # Add staff summary row
        hierarchical_data.append({
            'Staff Name': f"📊 {employee} - TOTALS",
            'Date': '',
            'Clock-In': '',
            'Clock-Out': '',
            'Standard Hours': data['Standard'],
            'Enhanced Hours': data['Enhanced'],
            'Supervisor Hours': data['Supervisor'],
            'Total Hours': data['total_hours'],
            'Total Shifts': data['total_shifts'],
            'Pay Rate Type': '',
            'Supervisor Flag': ''
        })
        
        # Add individual shifts for this staff member
        for entry in entries_sorted:
            # Handle both TimeEntry objects and tuples for backward compatibility
            if hasattr(entry, 'employee'):
                # TimeEntry object
                emp = entry.employee
                clock_in = entry.clock_in
                clock_out = entry.clock_out
                pay_rate_type = entry.pay_rate_type.value if hasattr(entry.pay_rate_type, 'value') else entry.pay_rate_type
            else:
                # Tuple format (backward compatibility)
                entry_id, emp, clock_in, clock_out, pay_rate_type, created_at = entry
            
            if emp.strip().lower() == employee.strip().lower():
                is_supervisor = (pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
                
                # Create a display string for the shift
                if is_supervisor:
                    shift_display = f"Supervisor ({split['Supervisor']}h)"
                elif split['Standard'] > 0 and split['Enhanced'] > 0:
                    shift_display = f"Mixed: {split['Standard']}h Standard, {split['Enhanced']}h Enhanced"
                elif split['Enhanced'] > 0:
                    shift_display = f"Enhanced ({split['Enhanced']}h)"
                else:
                    shift_display = f"Standard ({split['Standard']}h)"
                
                hierarchical_data.append({
                    'Staff Name': f"  └─ {employee}",
                    'Date': get_bst_time(clock_in).strftime('%Y-%m-%d'),
                    'Clock-In': get_bst_time(clock_in).strftime('%H:%M:%S'),
                    'Clock-Out': get_bst_time(clock_out).strftime('%H:%M:%S') if clock_out else 'In Progress',
                    'Standard Hours': split['Standard'],
                    'Enhanced Hours': split['Enhanced'],
                    'Supervisor Hours': split['Supervisor'],
                    'Total Hours': sum(split.values()),
                    'Total Shifts': '',
                    'Pay Rate Type': shift_display,
                    'Supervisor Flag': 'Yes' if pay_rate_type == "Supervisor" else 'No'
                })
        
        # Add blank row between staff members
        hierarchical_data.append({
            'Staff Name': '',
            'Date': '',
            'Clock-In': '',
            'Clock-Out': '',
            'Standard Hours': '',
            'Enhanced Hours': '',
            'Supervisor Hours': '',
            'Total Hours': '',
            'Total Shifts': '',
            'Pay Rate Type': '',
            'Supervisor Flag': ''
        })
    
    # Create DataFrame
    df_hierarchical = pd.DataFrame(hierarchical_data)
    
    # Calculate overall summary
    overall_summary = calculate_summary(entries)
    
    # Create Excel file with multiple sheets
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Hierarchical view (main sheet)
        df_hierarchical.to_excel(writer, sheet_name='Staff Hours & Shifts', index=False)
        
        # Overall summary sheet
        summary_data = {
            'Metric': ['Total Hours', 'Total Shifts', 'Unique Employees'],
            'Value': [overall_summary['total_hours'], overall_summary['total_shifts'], overall_summary['unique_employees']]
        }
        if start_date and end_date:
            summary_data['Metric'].extend(['Date Range'])
            summary_data['Value'].extend([f"{start_date} to {end_date}"])
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Overall Summary', index=False)
    
    return filename

def export_to_pdf(entries, filename="timesheet_export.pdf"):
    """Export timesheet data to PDF with staff summaries and individual shifts grouped under each staff member"""
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
    title = Paragraph("The Tythe Barn - Staff Hours & Shifts", title_style)
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
    Unique Employees: {overall_summary['unique_employees']}<br/>
    """
    summary_para = Paragraph(summary_text, styles['Normal'])
    story.append(summary_para)
    story.append(Spacer(1, 20))
    
    # Sort entries by employee and clock_in
    # Handle both TimeEntry objects and tuples for backward compatibility
    if entries and hasattr(entries[0], 'employee'):
        # TimeEntry objects
        entries_sorted = sorted(entries, key=lambda e: (e.employee.strip().lower(), e.clock_in))
    else:
        # Tuple format (backward compatibility)
        entries_sorted = sorted(entries, key=lambda e: (e[1].strip().lower(), e[2]))
    
    # For each staff member, show totals and then their shifts
    for employee, data in staff_summary.items():
        # Staff summary row
        staff_title = Paragraph(f"<b>{employee} - TOTALS</b>", styles['Heading3'])
        story.append(staff_title)
        staff_table = Table([["Standard Hours", "Enhanced Hours", "Supervisor Hours", "Total Hours", "Total Shifts"],
                             [str(data['Standard']), str(data['Enhanced']), str(data['Supervisor']), str(data['total_hours']), str(data['total_shifts'])]])
        staff_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        story.append(staff_table)
        story.append(Spacer(1, 8))
        
        # Individual shifts for this staff member
        shift_rows = [["Date", "Clock-In", "Clock-Out", "Standard", "Enhanced", "Supervisor", "Total", "Type"]]
        for entry in entries_sorted:
            # Handle both TimeEntry objects and tuples for backward compatibility
            if hasattr(entry, 'employee'):
                # TimeEntry object
                emp = entry.employee
                clock_in = entry.clock_in
                clock_out = entry.clock_out
                pay_rate_type = entry.pay_rate_type.value if hasattr(entry.pay_rate_type, 'value') else entry.pay_rate_type
            else:
                # Tuple format (backward compatibility)
                entry_id, emp, clock_in, clock_out, pay_rate_type, created_at = entry
            
            if emp.strip().lower() == employee.strip().lower():
                is_supervisor = (pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
                if is_supervisor:
                    shift_display = f"Supervisor ({split['Supervisor']}h)"
                elif split['Standard'] > 0 and split['Enhanced'] > 0:
                    shift_display = f"Mixed: {split['Standard']}h Std, {split['Enhanced']}h Enh"
                elif split['Enhanced'] > 0:
                    shift_display = f"Enhanced ({split['Enhanced']}h)"
                else:
                    shift_display = f"Standard ({split['Standard']}h)"
                shift_rows.append([
                    get_bst_time(clock_in).strftime('%Y-%m-%d'),
                    get_bst_time(clock_in).strftime('%H:%M'),
                    get_bst_time(clock_out).strftime('%H:%M') if clock_out else 'In Progress',
                    str(split['Standard']),
                    str(split['Enhanced']),
                    str(split['Supervisor']),
                    str(sum(split.values())),
                    shift_display
                ])
        if len(shift_rows) > 1:
            shift_table = Table(shift_rows)
            shift_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            story.append(shift_table)
            story.append(Spacer(1, 16))
        else:
            story.append(Paragraph("No shifts for this period.", styles['Normal']))
            story.append(Spacer(1, 16))
    
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

def get_hierarchical_staff_shift_data(entries):
    """
    Returns a list of dicts: staff total row, then their shifts, then blank row, for all staff.
    Each dict has keys: Staff Name, Date, Clock-In, Clock-Out, Standard Hours, Enhanced Hours, Supervisor Hours, Total Hours, Total Shifts, Pay Rate Type, Supervisor Flag
    """
    staff_summary = calculate_staff_summary(entries)
    # Sort entries by employee (case-insensitive, trimmed) and clock_in
    entries_sorted = sorted(entries, key=lambda e: (e[1].strip().lower(), e[2]))
    hierarchical_data = []
    for employee, data in staff_summary.items():
        # Add staff summary row
        hierarchical_data.append({
            'Staff Name': f"📊 {employee} - TOTALS",
            'Date': '',
            'Clock-In': '',
            'Clock-Out': '',
            'Standard Hours': data['Standard'],
            'Enhanced Hours': data['Enhanced'],
            'Supervisor Hours': data['Supervisor'],
            'Total Hours': data['total_hours'],
            'Total Shifts': data['total_shifts'],
            'Pay Rate Type': '',
            'Supervisor Flag': ''
        })
        # Add individual shifts for this staff member
        for entry in entries_sorted:
            entry_id, emp, clock_in, clock_out, pay_rate_type, created_at = entry
            if emp.strip().lower() == employee.strip().lower():
                is_supervisor = (pay_rate_type == 'Supervisor')
                split = split_shift_by_rate(clock_in, clock_out, is_supervisor)
                if is_supervisor:
                    shift_display = f"Supervisor ({split['Supervisor']}h)"
                elif split['Standard'] > 0 and split['Enhanced'] > 0:
                    shift_display = f"Mixed: {split['Standard']}h Standard, {split['Enhanced']}h Enhanced"
                elif split['Enhanced'] > 0:
                    shift_display = f"Enhanced ({split['Enhanced']}h)"
                else:
                    shift_display = f"Standard ({split['Standard']}h)"
                hierarchical_data.append({
                    'Staff Name': f"  └─ {employee}",
                    'Date': get_bst_time(clock_in).strftime('%Y-%m-%d'),
                    'Clock-In': get_bst_time(clock_in).strftime('%H:%M:%S'),
                    'Clock-Out': get_bst_time(clock_out).strftime('%H:%M:%S') if clock_out else 'In Progress',
                    'Standard Hours': split['Standard'],
                    'Enhanced Hours': split['Enhanced'],
                    'Supervisor Hours': split['Supervisor'],
                    'Total Hours': sum(split.values()),
                    'Total Shifts': '',
                    'Pay Rate Type': shift_display,
                    'Supervisor Flag': 'Yes' if pay_rate_type == "Supervisor" else 'No'
                })
        # Add blank row between staff members
        hierarchical_data.append({
            'Staff Name': '',
            'Date': '',
            'Clock-In': '',
            'Clock-Out': '',
            'Standard Hours': '',
            'Enhanced Hours': '',
            'Supervisor Hours': '',
            'Total Hours': '',
            'Total Shifts': '',
            'Pay Rate Type': '',
            'Supervisor Flag': ''
        })
    return hierarchical_data 