"""Business logic services for time tracking operations."""

import logging
from datetime import datetime, timedelta, timezone, date, time
from typing import List, Optional, Tuple

from .constants import PayRateType, TimeConstants
from .models import (
    ClockInRequest, ClockOutRequest, ExportRequest, OverallSummary, 
    ShiftRequest, StaffSummary, TimeEntry, TimeSplit
)
from ..database.repository import TimeEntryRepository
from ..database.connection import get_db_connection, DatabaseConnection
from ..utils.time_utils import TimeUtils

logger = logging.getLogger(__name__)


class TimeTrackingService:
    """Service for time tracking business logic operations."""
    
    def __init__(self, repository: Optional[TimeEntryRepository] = None) -> None:
        """Initialize the service with a repository.
        
        Args:
            repository: Time entry repository instance. If None, creates a default one.
        """
        if repository is None:
            conn = get_db_connection()
            if conn is None:
                raise ValueError("Could not establish database connection")
            db_connection = DatabaseConnection(conn)
            self.repository = TimeEntryRepository(db_connection)
        else:
            self.repository = repository
    
    def clock_in(self, employee_name: str, is_supervisor: bool) -> Tuple[bool, str]:
        """Clock in an employee (simplified interface for UI).
        
        Args:
            employee_name: Name of the employee.
            is_supervisor: Whether the employee is a supervisor.
            
        Returns:
            Tuple of (success, message).
        """
        request = ClockInRequest(employee_name=employee_name, is_supervisor=is_supervisor)
        return self.clock_in_with_request(request)
    
    def clock_in_with_request(self, request: ClockInRequest) -> Tuple[bool, str]:
        """Clock in an employee.
        
        Args:
            request: Clock in request containing employee name and supervisor status.
            
        Returns:
            Tuple of (success, message).
        """
        try:
            # Check if employee already has an open shift
            existing_shift = self.repository.get_open_shift(request.employee_name)
            if existing_shift:
                return False, f"{request.employee_name} already has an open shift"
            
            # Determine pay rate type
            current_time = datetime.now(timezone.utc)
            pay_rate_type = self._determine_pay_rate_type(request.is_supervisor, current_time)
            
            # Create time entry
            time_entry = self.repository.create_time_entry(
                employee=request.employee_name,
                clock_in=current_time,
                pay_rate_type=pay_rate_type
            )
            
            rate_message = f" ({pay_rate_type.value} Rate)"
            return True, f"{request.employee_name} clocked in successfully{rate_message}"
            
        except Exception as e:
            logger.error(f"Error clocking in {request.employee_name}: {e}")
            return False, f"Error clocking in: {e}"
    
    def clock_out(self, employee_name: str) -> Tuple[bool, str]:
        """Clock out an employee (simplified interface for UI).
        
        Args:
            employee_name: Name of the employee.
            
        Returns:
            Tuple of (success, message).
        """
        request = ClockOutRequest(employee_name=employee_name)
        return self.clock_out_with_request(request)
    
    def clock_out_with_request(self, request: ClockOutRequest) -> Tuple[bool, str]:
        """Clock out an employee.
        
        Args:
            request: Clock out request containing employee name.
            
        Returns:
            Tuple of (success, message).
        """
        try:
            # Find the most recent open shift for this employee
            open_shift = self.repository.get_open_shift(request.employee_name)
            if not open_shift:
                return False, f"No open shift found for {request.employee_name}"
            
            # Close the shift
            current_time = datetime.now(timezone.utc)
            self.repository.close_shift(open_shift.id, current_time)
            
            return True, f"{request.employee_name} clocked out successfully"
            
        except Exception as e:
            logger.error(f"Error clocking out {request.employee_name}: {e}")
            return False, f"Error clocking out: {e}"
    
    def get_open_shift(self, employee_name: str) -> Optional[TimeEntry]:
        """Get the open shift for an employee.
        
        Args:
            employee_name: Name of the employee.
            
        Returns:
            TimeEntry if open shift exists, None otherwise.
        """
        return self.repository.get_open_shift(employee_name)
    
    def get_employee_timesheet(
        self, 
        employee: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TimeEntry]:
        """Get timesheet for a specific employee.
        
        Args:
            employee: Employee name.
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            
        Returns:
            List of time entries.
        """
        return self.repository.get_employee_timesheet(employee, start_date, end_date)
    
    def get_all_timesheets(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[TimeEntry]:
        """Get all timesheet entries.
        
        Args:
            start_date: Optional start date filter.
            end_date: Optional end date filter.
            
        Returns:
            List of all time entries.
        """
        return self.repository.get_all_timesheets(start_date, end_date)
    
    def add_shift_manually(
        self,
        employee_name: str,
        clock_in_date: date,
        clock_in_time: time,
        clock_out_date: Optional[date],
        clock_out_time: Optional[time],
        is_supervisor: bool,
        pay_rate_override: Optional[str]
    ) -> Tuple[bool, str]:
        """Add a shift manually for managers (simplified interface for UI).
        
        Args:
            employee_name: Name of the employee.
            clock_in_date: Clock-in date.
            clock_in_time: Clock-in time.
            clock_out_date: Optional clock-out date.
            clock_out_time: Optional clock-out time.
            is_supervisor: Whether the employee is a supervisor.
            pay_rate_override: Optional pay rate override.
            
        Returns:
            Tuple of (success, message).
        """
        request = ShiftRequest(
            employee_name=employee_name,
            clock_in_date=datetime.combine(clock_in_date, clock_in_time),
            clock_in_time=datetime.combine(clock_in_date, clock_in_time),
            clock_out_date=datetime.combine(clock_out_date, clock_out_time) if clock_out_date and clock_out_time else None,
            clock_out_time=datetime.combine(clock_out_date, clock_out_time) if clock_out_date and clock_out_time else None,
            is_supervisor=is_supervisor,
            pay_rate_override=PayRateType(pay_rate_override) if pay_rate_override else None
        )
        return self.add_shift_manually_with_request(request)
    
    def add_shift_manually_with_request(self, request: ShiftRequest) -> Tuple[bool, str]:
        """Add a shift manually for managers.
        
        Args:
            request: Shift request containing all shift details.
            
        Returns:
            Tuple of (success, message).
        """
        try:
            # Combine date and time for clock-in
            clock_in_datetime = datetime.combine(
                request.clock_in_date.date(), 
                request.clock_in_time.time()
            )
            clock_in_datetime = TimeUtils.convert_to_utc(clock_in_datetime)
            
            # Combine date and time for clock-out (if provided)
            clock_out_datetime = None
            if request.clock_out_date and request.clock_out_time:
                clock_out_datetime = datetime.combine(
                    request.clock_out_date.date(), 
                    request.clock_out_time.time()
                )
                clock_out_datetime = TimeUtils.convert_to_utc(clock_out_datetime)
            
            # Determine pay rate type
            if request.pay_rate_override:
                pay_rate_type = request.pay_rate_override
            else:
                pay_rate_type = self._determine_pay_rate_type(
                    request.is_supervisor, clock_in_datetime
                )
            
            # Create time entry
            time_entry = self.repository.create_time_entry(
                employee=request.employee_name,
                clock_in=clock_in_datetime,
                clock_out=clock_out_datetime,
                pay_rate_type=pay_rate_type
            )
            
            return True, f"Shift added for {request.employee_name} ({pay_rate_type.value} Rate)"
            
        except Exception as e:
            logger.error(f"Error adding shift for {request.employee_name}: {e}")
            return False, f"Error adding shift: {e}"
    
    def edit_shift(
        self,
        entry_id: str,
        employee_name: str,
        clock_in_date: date,
        clock_in_time: time,
        clock_out_date: Optional[date],
        clock_out_time: Optional[time],
        is_supervisor: bool,
        pay_rate_override: Optional[str]
    ) -> Tuple[bool, str]:
        """Edit an existing shift (simplified interface for UI).
        
        Args:
            entry_id: The ID of the time entry to edit.
            employee_name: Name of the employee.
            clock_in_date: Clock-in date.
            clock_in_time: Clock-in time.
            clock_out_date: Optional clock-out date.
            clock_out_time: Optional clock-out time.
            is_supervisor: Whether the employee is a supervisor.
            pay_rate_override: Optional pay rate override.
            
        Returns:
            Tuple of (success, message).
        """
        request = ShiftRequest(
            employee_name=employee_name,
            clock_in_date=datetime.combine(clock_in_date, clock_in_time),
            clock_in_time=datetime.combine(clock_in_date, clock_in_time),
            clock_out_date=datetime.combine(clock_out_date, clock_out_time) if clock_out_date and clock_out_time else None,
            clock_out_time=datetime.combine(clock_out_date, clock_out_time) if clock_out_date and clock_out_time else None,
            is_supervisor=is_supervisor,
            pay_rate_override=PayRateType(pay_rate_override) if pay_rate_override else None
        )
        return self.edit_shift_with_request(entry_id, request)
    
    def edit_shift_with_request(self, entry_id: str, request: ShiftRequest) -> Tuple[bool, str]:
        """Edit an existing shift.
        
        Args:
            entry_id: The ID of the time entry to edit.
            request: Shift request containing updated details.
            
        Returns:
            Tuple of (success, message).
        """
        try:
            # Combine date and time for clock-in
            clock_in_datetime = datetime.combine(
                request.clock_in_date.date(), 
                request.clock_in_time.time()
            )
            clock_in_datetime = TimeUtils.convert_to_utc(clock_in_datetime)
            
            # Combine date and time for clock-out (if provided)
            clock_out_datetime = None
            if request.clock_out_date and request.clock_out_time:
                clock_out_datetime = datetime.combine(
                    request.clock_out_date.date(), 
                    request.clock_out_time.time()
                )
                clock_out_datetime = TimeUtils.convert_to_utc(clock_out_datetime)
            
            # Determine pay rate type
            if request.pay_rate_override:
                pay_rate_type = request.pay_rate_override
            else:
                pay_rate_type = self._determine_pay_rate_type(
                    request.is_supervisor, clock_in_datetime
                )
            
            # Update the time entry
            updated = self.repository.update_time_entry(
                entry_id=entry_id,
                employee=request.employee_name,
                clock_in=clock_in_datetime,
                clock_out=clock_out_datetime,
                pay_rate_type=pay_rate_type
            )
            
            if not updated:
                return False, "Shift not found"
            
            return True, f"Shift updated for {request.employee_name} ({pay_rate_type.value} Rate)"
            
        except Exception as e:
            logger.error(f"Error updating shift {entry_id}: {e}")
            return False, f"Error updating shift: {e}"
    
    def delete_entry(self, entry_id: str) -> Tuple[bool, str]:
        """Delete a time entry.
        
        Args:
            entry_id: The ID of the time entry to delete.
            
        Returns:
            Tuple of (success, message).
        """
        try:
            deleted = self.repository.delete_time_entry(entry_id)
            if deleted:
                return True, "Entry deleted successfully"
            else:
                return False, "Entry not found"
                
        except Exception as e:
            logger.error(f"Error deleting entry {entry_id}: {e}")
            return False, f"Error deleting entry: {e}"
    
    def get_shift_by_id(self, entry_id: str) -> Optional[TimeEntry]:
        """Get a specific shift by ID.
        
        Args:
            entry_id: The ID of the time entry.
            
        Returns:
            TimeEntry if found, None otherwise.
        """
        return self.repository.get_time_entry_by_id(entry_id)
    
    def calculate_time_split(self, time_entry: TimeEntry) -> TimeSplit:
        """Calculate the time split for a time entry.
        
        Args:
            time_entry: The time entry to calculate split for.
            
        Returns:
            TimeSplit containing the calculated hours.
        """
        if not time_entry.clock_out:
            return TimeSplit(standard_hours=0.0, enhanced_hours=0.0, supervisor_hours=0.0)
        
        # Calculate total duration
        duration = time_entry.clock_out - time_entry.clock_in
        total_hours = duration.total_seconds() / 3600
        
        # If supervisor, all hours are supervisor hours
        if time_entry.pay_rate_type == PayRateType.SUPERVISOR:
            return TimeSplit(
                standard_hours=0.0,
                enhanced_hours=0.0,
                supervisor_hours=total_hours
            )
        
        # Calculate split based on clock-in time
        clock_in_hour = time_entry.clock_in.hour
        
        # Enhanced hours: 7 PM (19:00) to 4 AM (04:00)
        if clock_in_hour >= 19 or clock_in_hour < 4:
            return TimeSplit(
                standard_hours=0.0,
                enhanced_hours=total_hours,
                supervisor_hours=0.0
            )
        else:
            return TimeSplit(
                standard_hours=total_hours,
                enhanced_hours=0.0,
                supervisor_hours=0.0
            )
    
    def calculate_staff_summary(self, entries: List[TimeEntry]) -> dict[str, StaffSummary]:
        """Calculate summary statistics for each staff member.
        
        Args:
            entries: List of time entries.
            
        Returns:
            Dictionary mapping employee names to their summaries.
        """
        staff_summaries = {}
        
        for entry in entries:
            if entry.employee not in staff_summaries:
                staff_summaries[entry.employee] = StaffSummary(
                    employee_name=entry.employee,
                    total_hours=0.0,
                    total_shifts=0,
                    standard_hours=0.0,
                    enhanced_hours=0.0,
                    supervisor_hours=0.0
                )
            
            summary = staff_summaries[entry.employee]
            time_split = self.calculate_time_split(entry)
            
            summary.total_hours += time_split.total_hours
            summary.total_shifts += 1
            summary.standard_hours += time_split.standard_hours
            summary.enhanced_hours += time_split.enhanced_hours
            summary.supervisor_hours += time_split.supervisor_hours
        
        return staff_summaries
    
    def calculate_overall_summary(self, entries: List[TimeEntry]) -> OverallSummary:
        """Calculate overall summary statistics.
        
        Args:
            entries: List of time entries.
            
        Returns:
            OverallSummary containing the calculated statistics.
        """
        if not entries:
            return OverallSummary(
                total_hours=0.0,
                total_shifts=0,
                unique_employees=0,
                staff_summary={}
            )
        
        staff_summaries = self.calculate_staff_summary(entries)
        
        total_hours = sum(summary.total_hours for summary in staff_summaries.values())
        total_shifts = sum(summary.total_shifts for summary in staff_summaries.values())
        unique_employees = len(staff_summaries)
        
        return OverallSummary(
            total_hours=total_hours,
            total_shifts=total_shifts,
            unique_employees=unique_employees,
            staff_summary=staff_summaries
        )
    
    def _determine_pay_rate_type(
        self, 
        is_supervisor: bool, 
        clock_in_time: Optional[datetime] = None
    ) -> PayRateType:
        """Determine the pay rate type based on time and supervisor status.
        
        Args:
            is_supervisor: Whether the employee is a supervisor.
            clock_in_time: The clock-in time. If None, uses current time.
            
        Returns:
            PayRateType for the shift.
        """
        if is_supervisor:
            return PayRateType.SUPERVISOR
        
        if clock_in_time is None:
            clock_in_time = datetime.now(timezone.utc)
        
        # Convert to BST for hour calculation
        bst_time = TimeUtils.convert_to_bst(clock_in_time)
        hour = bst_time.hour
        
        # Enhanced rate: 7:00 PM (19:00) to 4:00 AM (04:00) in BST
        if hour >= 19 or hour < 4:
            return PayRateType.ENHANCED
        else:
            return PayRateType.STANDARD 