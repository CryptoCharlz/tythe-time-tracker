"""Business logic services for time tracking operations."""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from .constants import PayRateType, TimeConstants
from .models import (
    ClockInRequest, ClockOutRequest, ExportRequest, OverallSummary, 
    ShiftRequest, StaffSummary, TimeEntry, TimeSplit
)
from ..database.repository import TimeEntryRepository
from ..utils.time_utils import TimeUtils

logger = logging.getLogger(__name__)


class TimeTrackingService:
    """Service for time tracking business logic operations."""
    
    def __init__(self, repository: TimeEntryRepository) -> None:
        """Initialize the service with a repository.
        
        Args:
            repository: Time entry repository instance.
        """
        self.repository = repository
    
    def clock_in(self, request: ClockInRequest) -> Tuple[bool, str]:
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
    
    def clock_out(self, request: ClockOutRequest) -> Tuple[bool, str]:
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
    
    def add_shift_manually(self, request: ShiftRequest) -> Tuple[bool, str]:
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
    
    def edit_shift(self, entry_id: str, request: ShiftRequest) -> Tuple[bool, str]:
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
            
            # Update time entry
            time_entry = self.repository.update_time_entry(
                entry_id=entry_id,
                employee=request.employee_name,
                clock_in=clock_in_datetime,
                clock_out=clock_out_datetime,
                pay_rate_type=pay_rate_type
            )
            
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
            success = self.repository.delete_time_entry(entry_id)
            if success:
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
            The time entry if found, None otherwise.
        """
        return self.repository.get_time_entry_by_id(entry_id)
    
    def calculate_time_split(self, time_entry: TimeEntry) -> TimeSplit:
        """Calculate the split of hours by pay rate type for a time entry.
        
        Args:
            time_entry: The time entry to calculate split for.
            
        Returns:
            TimeSplit instance with hours by rate type.
        """
        if not time_entry.clock_out:
            return TimeSplit(standard_hours=0, enhanced_hours=0, supervisor_hours=0)
        
        if time_entry.pay_rate_type == PayRateType.SUPERVISOR:
            total_hours = time_entry.duration_hours or 0
            return TimeSplit(
                standard_hours=0, 
                enhanced_hours=0, 
                supervisor_hours=round(total_hours, TimeConstants.HOURS_PRECISION)
            )
        
        # Convert to BST for rate calculations
        bst_in = TimeUtils.convert_to_bst(time_entry.clock_in)
        bst_out = TimeUtils.convert_to_bst(time_entry.clock_out)
        
        # Calculate boundaries
        day = bst_in.date()
        seven_pm = datetime.combine(day, TimeConstants.ENHANCED_START_TIME)
        four_am_next = datetime.combine(day + timedelta(days=1), TimeConstants.ENHANCED_END_TIME)
        
        # If shift ends before 7PM
        if bst_out <= seven_pm:
            std_hours = (bst_out - bst_in).total_seconds() / 3600
            return TimeSplit(
                standard_hours=round(std_hours, TimeConstants.HOURS_PRECISION),
                enhanced_hours=0,
                supervisor_hours=0
            )
        
        # If shift starts after 7PM and before 4AM
        if bst_in >= seven_pm and bst_in < four_am_next:
            enh_hours = (min(bst_out, four_am_next) - bst_in).total_seconds() / 3600
            std_hours = max((bst_out - four_am_next).total_seconds() / 3600, 0) if bst_out > four_am_next else 0
            return TimeSplit(
                standard_hours=round(std_hours, TimeConstants.HOURS_PRECISION),
                enhanced_hours=round(enh_hours, TimeConstants.HOURS_PRECISION),
                supervisor_hours=0
            )
        
        # If shift starts before 7PM and ends after 7PM
        std_hours = (seven_pm - bst_in).total_seconds() / 3600 if bst_in < seven_pm else 0
        enh_hours = (min(bst_out, four_am_next) - max(bst_in, seven_pm)).total_seconds() / 3600 if bst_out > seven_pm else 0
        std2_hours = (bst_out - four_am_next).total_seconds() / 3600 if bst_out > four_am_next else 0
        
        return TimeSplit(
            standard_hours=round(std_hours + max(std2_hours, 0), TimeConstants.HOURS_PRECISION),
            enhanced_hours=round(max(enh_hours, 0), TimeConstants.HOURS_PRECISION),
            supervisor_hours=0
        )
    
    def calculate_staff_summary(self, entries: List[TimeEntry]) -> dict[str, StaffSummary]:
        """Calculate summary by staff member with hours per pay rate type.
        
        Args:
            entries: List of time entries to summarize.
            
        Returns:
            Dictionary mapping employee names to their summaries.
        """
        staff_summaries = {}
        
        for entry in entries:
            time_split = self.calculate_time_split(entry)
            
            if entry.employee not in staff_summaries:
                staff_summaries[entry.employee] = StaffSummary(
                    employee=entry.employee,
                    standard_hours=0,
                    enhanced_hours=0,
                    supervisor_hours=0,
                    total_shifts=0
                )
            
            # Add hours to the appropriate pay rate type
            current_summary = staff_summaries[entry.employee]
            staff_summaries[entry.employee] = StaffSummary(
                employee=entry.employee,
                standard_hours=current_summary.standard_hours + time_split.standard_hours,
                enhanced_hours=current_summary.enhanced_hours + time_split.enhanced_hours,
                supervisor_hours=current_summary.supervisor_hours + time_split.supervisor_hours,
                total_shifts=current_summary.total_shifts + 1
            )
        
        return staff_summaries
    
    def calculate_overall_summary(self, entries: List[TimeEntry]) -> OverallSummary:
        """Calculate overall summary statistics.
        
        Args:
            entries: List of time entries to summarize.
            
        Returns:
            OverallSummary instance with aggregate statistics.
        """
        staff_summaries = self.calculate_staff_summary(entries)
        
        total_hours = sum(staff.total_hours for staff in staff_summaries.values())
        total_shifts = sum(staff.total_shifts for staff in staff_summaries.values())
        unique_employees = len(staff_summaries)
        
        return OverallSummary(
            total_hours=round(total_hours, TimeConstants.HOURS_PRECISION),
            total_shifts=total_shifts,
            unique_employees=unique_employees,
            staff_summaries=staff_summaries
        )
    
    def _determine_pay_rate_type(
        self, 
        is_supervisor: bool, 
        clock_in_time: Optional[datetime] = None
    ) -> PayRateType:
        """Determine the pay rate type based on time and supervisor status.
        
        Args:
            is_supervisor: Whether the employee is a supervisor.
            clock_in_time: Clock in time (defaults to current time).
            
        Returns:
            PayRateType enum value.
        """
        if is_supervisor:
            return PayRateType.SUPERVISOR
        
        if clock_in_time is None:
            clock_in_time = datetime.now(timezone.utc)
        
        # Check if it's enhanced hours in BST
        if TimeUtils.is_enhanced_hours(clock_in_time):
            return PayRateType.ENHANCED
        else:
            return PayRateType.STANDARD 