"""Data models for the time tracking application."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from .constants import PayRateType


@dataclass(frozen=True)
class TimeEntry:
    """Represents a time entry in the system."""
    
    id: UUID
    employee: str
    clock_in: datetime
    clock_out: Optional[datetime]
    pay_rate_type: PayRateType
    created_at: datetime
    
    def __post_init__(self) -> None:
        """Validate the time entry data."""
        if not self.employee.strip():
            raise ValueError("Employee name cannot be empty")
        
        if self.clock_out and self.clock_out <= self.clock_in:
            raise ValueError("Clock out time must be after clock in time")
    
    @property
    def is_open(self) -> bool:
        """Check if the time entry is still open (no clock out time)."""
        return self.clock_out is None
    
    @property
    def duration_hours(self) -> Optional[float]:
        """Calculate the duration in hours if the entry is closed."""
        if not self.clock_out:
            return None
        
        duration = self.clock_out - self.clock_in
        return round(duration.total_seconds() / 3600, 2)


@dataclass(frozen=True)
class TimeSplit:
    """Represents the split of hours by pay rate type."""
    
    standard_hours: float
    enhanced_hours: float
    supervisor_hours: float
    
    @property
    def total_hours(self) -> float:
        """Calculate total hours across all rate types."""
        return self.standard_hours + self.enhanced_hours + self.supervisor_hours
    
    def __add__(self, other: "TimeSplit") -> "TimeSplit":
        """Add two time splits together."""
        return TimeSplit(
            standard_hours=self.standard_hours + other.standard_hours,
            enhanced_hours=self.enhanced_hours + other.enhanced_hours,
            supervisor_hours=self.supervisor_hours + other.supervisor_hours,
        )


@dataclass(frozen=True)
class StaffSummary:
    """Summary of hours worked by a staff member."""
    
    employee: str
    standard_hours: float
    enhanced_hours: float
    supervisor_hours: float
    total_shifts: int
    
    @property
    def total_hours(self) -> float:
        """Calculate total hours worked."""
        return self.standard_hours + self.enhanced_hours + self.supervisor_hours


@dataclass(frozen=True)
class OverallSummary:
    """Overall summary of all time entries."""
    
    total_hours: float
    total_shifts: int
    unique_employees: int
    staff_summaries: dict[str, StaffSummary]


@dataclass(frozen=True)
class ExportRequest:
    """Request parameters for exporting timesheet data."""
    
    employee_name: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_manager: bool
    export_format: str
    role_filter: str = "All Roles"
    
    def __post_init__(self) -> None:
        """Validate export request parameters."""
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        
        if self.export_format not in ["Excel (.xlsx)", "PDF"]:
            raise ValueError("Invalid export format")


@dataclass(frozen=True)
class ClockInRequest:
    """Request parameters for clocking in."""
    
    employee_name: str
    is_supervisor: bool
    
    def __post_init__(self) -> None:
        """Validate clock in request."""
        if not self.employee_name.strip():
            raise ValueError("Employee name cannot be empty")


@dataclass(frozen=True)
class ClockOutRequest:
    """Request parameters for clocking out."""
    
    employee_name: str
    
    def __post_init__(self) -> None:
        """Validate clock out request."""
        if not self.employee_name.strip():
            raise ValueError("Employee name cannot be empty")


@dataclass(frozen=True)
class ShiftRequest:
    """Request parameters for adding or editing a shift."""
    
    employee_name: str
    clock_in_date: datetime
    clock_in_time: datetime
    clock_out_date: Optional[datetime]
    clock_out_time: Optional[datetime]
    is_supervisor: bool
    pay_rate_override: Optional[PayRateType]
    
    def __post_init__(self) -> None:
        """Validate shift request."""
        if not self.employee_name.strip():
            raise ValueError("Employee name cannot be empty")
        
        if self.clock_out_date and self.clock_out_time:
            clock_out_datetime = datetime.combine(
                self.clock_out_date.date(), self.clock_out_time.time()
            )
            clock_in_datetime = datetime.combine(
                self.clock_in_date.date(), self.clock_in_time.time()
            )
            
            if clock_out_datetime <= clock_in_datetime:
                raise ValueError("Clock out time must be after clock in time") 