"""Constants used throughout the time tracking application."""

from datetime import time
from enum import Enum
from typing import Final


class PayRateType(str, Enum):
    """Pay rate types for time tracking."""
    
    STANDARD = "Standard"
    ENHANCED = "Enhanced"
    SUPERVISOR = "Supervisor"


class TimeConstants:
    """Constants related to time calculations and business rules."""
    
    # BST (British Summer Time) offset from UTC
    BST_OFFSET_HOURS: Final[int] = 1
    
    # Enhanced rate hours (7:00 PM to 4:00 AM BST)
    ENHANCED_START_HOUR: Final[int] = 19  # 7:00 PM
    ENHANCED_END_HOUR: Final[int] = 4     # 4:00 AM
    
    # Time boundaries
    ENHANCED_START_TIME: Final[time] = time(19, 0)  # 7:00 PM
    ENHANCED_END_TIME: Final[time] = time(4, 0)     # 4:00 AM
    
    # Rounding precision for hours
    HOURS_PRECISION: Final[int] = 2


class DatabaseConstants:
    """Database-related constants."""
    
    # Table names
    TIME_ENTRIES_TABLE: Final[str] = "time_entries"
    
    # Column names
    ID_COLUMN: Final[str] = "id"
    EMPLOYEE_COLUMN: Final[str] = "employee"
    CLOCK_IN_COLUMN: Final[str] = "clock_in"
    CLOCK_OUT_COLUMN: Final[str] = "clock_out"
    PAY_RATE_TYPE_COLUMN: Final[str] = "pay_rate_type"
    CREATED_AT_COLUMN: Final[str] = "created_at"


class UIConstants:
    """UI-related constants."""
    
    # Page titles
    APP_TITLE: Final[str] = "🕒 The Tythe Barn - Time Tracker"
    
    # Navigation options
    EMPLOYEE_CLOCK_PAGE: Final[str] = "Employee Clock In/Out"
    PERSONAL_TIMESHEET_PAGE: Final[str] = "Personal Timesheet"
    EXPORT_TIMESHEET_PAGE: Final[str] = "Export Timesheet"
    MANAGER_DASHBOARD_PAGE: Final[str] = "Manager Dashboard"
    
    # Export formats
    EXCEL_FORMAT: Final[str] = "Excel (.xlsx)"
    PDF_FORMAT: Final[str] = "PDF"
    
    # Date range options
    CUSTOM_RANGE: Final[str] = "Custom Range"
    THIS_WEEK: Final[str] = "This Week"
    LAST_WEEK: Final[str] = "Last Week"
    THIS_MONTH: Final[str] = "This Month"
    
    # Role filters
    ALL_ROLES: Final[str] = "All Roles"
    STAFF_ONLY: Final[str] = "Staff Only"
    SUPERVISORS_ONLY: Final[str] = "Supervisors Only"


class ExportConstants:
    """Export-related constants."""
    
    # File naming
    TIMESHEET_EXPORT_PREFIX: Final[str] = "timesheet_export"
    ALL_TIMESHEETS_PREFIX: Final[str] = "all_timesheets"
    
    # Excel sheet names
    STAFF_HOURS_SHEET: Final[str] = "Staff Hours & Shifts"
    OVERALL_SUMMARY_SHEET: Final[str] = "Overall Summary"
    
    # MIME types
    EXCEL_MIME_TYPE: Final[str] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    PDF_MIME_TYPE: Final[str] = "application/pdf"


class ErrorMessages:
    """Standard error messages."""
    
    # Database errors
    DB_CONNECTION_FAILED: Final[str] = "Database connection failed"
    DB_INIT_FAILED: Final[str] = "Database initialization failed"
    
    # Clock in/out errors
    ALREADY_CLOCKED_IN: Final[str] = "already has an open shift"
    NO_OPEN_SHIFT: Final[str] = "No open shift found for"
    CLOCK_IN_ERROR: Final[str] = "Error clocking in"
    CLOCK_OUT_ERROR: Final[str] = "Error clocking out"
    
    # Validation errors
    END_DATE_BEFORE_START: Final[str] = "End date cannot be before start date"
    EMPLOYEE_NAME_REQUIRED: Final[str] = "Please enter an employee name"
    ENTRY_ID_REQUIRED: Final[str] = "Please enter an Entry ID"
    SHIFT_NOT_FOUND: Final[str] = "Shift not found"
    
    # Authentication errors
    INCORRECT_PASSWORD: Final[str] = "Incorrect password" 