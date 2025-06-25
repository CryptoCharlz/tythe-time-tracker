"""Unit tests for data models."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from tythe_time_tracker.core.constants import PayRateType
from tythe_time_tracker.core.models import (
    TimeEntry, TimeSplit, StaffSummary, OverallSummary, 
    ClockInRequest, ClockOutRequest, ShiftRequest
)


class TestTimeEntry:
    """Test TimeEntry model."""
    
    def test_create_valid_time_entry(self):
        """Test creating a valid time entry."""
        entry_id = uuid4()
        clock_in = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        clock_out = datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
        created_at = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        
        entry = TimeEntry(
            id=entry_id,
            employee="John Doe",
            clock_in=clock_in,
            clock_out=clock_out,
            pay_rate_type=PayRateType.STANDARD,
            created_at=created_at
        )
        
        assert entry.id == entry_id
        assert entry.employee == "John Doe"
        assert entry.clock_in == clock_in
        assert entry.clock_out == clock_out
        assert entry.pay_rate_type == PayRateType.STANDARD
        assert entry.created_at == created_at
        assert not entry.is_open
        assert entry.duration_hours == 8.0
    
    def test_create_open_time_entry(self):
        """Test creating an open time entry (no clock out)."""
        entry = TimeEntry(
            id=uuid4(),
            employee="John Doe",
            clock_in=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            clock_out=None,
            pay_rate_type=PayRateType.STANDARD,
            created_at=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        )
        
        assert entry.is_open
        assert entry.duration_hours is None
    
    def test_time_entry_validation_empty_employee(self):
        """Test that empty employee name raises ValueError."""
        with pytest.raises(ValueError, match="Employee name cannot be empty"):
            TimeEntry(
                id=uuid4(),
                employee="",
                clock_in=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
                clock_out=datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc),
                pay_rate_type=PayRateType.STANDARD,
                created_at=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
            )
    
    def test_time_entry_validation_whitespace_employee(self):
        """Test that whitespace-only employee name raises ValueError."""
        with pytest.raises(ValueError, match="Employee name cannot be empty"):
            TimeEntry(
                id=uuid4(),
                employee="   ",
                clock_in=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
                clock_out=datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc),
                pay_rate_type=PayRateType.STANDARD,
                created_at=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
            )
    
    def test_time_entry_validation_invalid_clock_out(self):
        """Test that clock out before clock in raises ValueError."""
        with pytest.raises(ValueError, match="Clock out time must be after clock in time"):
            TimeEntry(
                id=uuid4(),
                employee="John Doe",
                clock_in=datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc),
                clock_out=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
                pay_rate_type=PayRateType.STANDARD,
                created_at=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
            )


class TestTimeSplit:
    """Test TimeSplit model."""
    
    def test_create_time_split(self):
        """Test creating a time split."""
        split = TimeSplit(
            standard_hours=6.0,
            enhanced_hours=2.0,
            supervisor_hours=0.0
        )
        
        assert split.standard_hours == 6.0
        assert split.enhanced_hours == 2.0
        assert split.supervisor_hours == 0.0
        assert split.total_hours == 8.0
    
    def test_add_time_splits(self):
        """Test adding two time splits together."""
        split1 = TimeSplit(standard_hours=4.0, enhanced_hours=1.0, supervisor_hours=0.0)
        split2 = TimeSplit(standard_hours=2.0, enhanced_hours=1.0, supervisor_hours=0.0)
        
        result = split1 + split2
        
        assert result.standard_hours == 6.0
        assert result.enhanced_hours == 2.0
        assert result.supervisor_hours == 0.0
        assert result.total_hours == 8.0


class TestStaffSummary:
    """Test StaffSummary model."""
    
    def test_create_staff_summary(self):
        """Test creating a staff summary."""
        summary = StaffSummary(
            employee="John Doe",
            standard_hours=40.0,
            enhanced_hours=8.0,
            supervisor_hours=0.0,
            total_shifts=5
        )
        
        assert summary.employee == "John Doe"
        assert summary.standard_hours == 40.0
        assert summary.enhanced_hours == 8.0
        assert summary.supervisor_hours == 0.0
        assert summary.total_shifts == 5
        assert summary.total_hours == 48.0


class TestOverallSummary:
    """Test OverallSummary model."""
    
    def test_create_overall_summary(self):
        """Test creating an overall summary."""
        staff_summaries = {
            "John Doe": StaffSummary(
                employee="John Doe",
                standard_hours=40.0,
                enhanced_hours=8.0,
                supervisor_hours=0.0,
                total_shifts=5
            ),
            "Jane Smith": StaffSummary(
                employee="Jane Smith",
                standard_hours=32.0,
                enhanced_hours=4.0,
                supervisor_hours=0.0,
                total_shifts=4
            )
        }
        
        summary = OverallSummary(
            total_hours=84.0,
            total_shifts=9,
            unique_employees=2,
            staff_summaries=staff_summaries
        )
        
        assert summary.total_hours == 84.0
        assert summary.total_shifts == 9
        assert summary.unique_employees == 2
        assert len(summary.staff_summaries) == 2


class TestClockInRequest:
    """Test ClockInRequest model."""
    
    def test_create_valid_clock_in_request(self):
        """Test creating a valid clock in request."""
        request = ClockInRequest(
            employee_name="John Doe",
            is_supervisor=False
        )
        
        assert request.employee_name == "John Doe"
        assert not request.is_supervisor
    
    def test_clock_in_request_validation_empty_employee(self):
        """Test that empty employee name raises ValueError."""
        with pytest.raises(ValueError, match="Employee name cannot be empty"):
            ClockInRequest(employee_name="", is_supervisor=False)
    
    def test_clock_in_request_validation_whitespace_employee(self):
        """Test that whitespace-only employee name raises ValueError."""
        with pytest.raises(ValueError, match="Employee name cannot be empty"):
            ClockInRequest(employee_name="   ", is_supervisor=False)


class TestClockOutRequest:
    """Test ClockOutRequest model."""
    
    def test_create_valid_clock_out_request(self):
        """Test creating a valid clock out request."""
        request = ClockOutRequest(employee_name="John Doe")
        
        assert request.employee_name == "John Doe"
    
    def test_clock_out_request_validation_empty_employee(self):
        """Test that empty employee name raises ValueError."""
        with pytest.raises(ValueError, match="Employee name cannot be empty"):
            ClockOutRequest(employee_name="")


class TestShiftRequest:
    """Test ShiftRequest model."""
    
    def test_create_valid_shift_request(self):
        """Test creating a valid shift request."""
        clock_in_date = datetime(2024, 1, 1, 9, 0, 0)
        clock_in_time = datetime(2024, 1, 1, 9, 0, 0)
        clock_out_date = datetime(2024, 1, 1, 17, 0, 0)
        clock_out_time = datetime(2024, 1, 1, 17, 0, 0)
        
        request = ShiftRequest(
            employee_name="John Doe",
            clock_in_date=clock_in_date,
            clock_in_time=clock_in_time,
            clock_out_date=clock_out_date,
            clock_out_time=clock_out_time,
            is_supervisor=False,
            pay_rate_override=None
        )
        
        assert request.employee_name == "John Doe"
        assert request.clock_in_date == clock_in_date
        assert request.clock_in_time == clock_in_time
        assert request.clock_out_date == clock_out_date
        assert request.clock_out_time == clock_out_time
        assert not request.is_supervisor
        assert request.pay_rate_override is None
    
    def test_shift_request_validation_empty_employee(self):
        """Test that empty employee name raises ValueError."""
        with pytest.raises(ValueError, match="Employee name cannot be empty"):
            ShiftRequest(
                employee_name="",
                clock_in_date=datetime(2024, 1, 1, 9, 0, 0),
                clock_in_time=datetime(2024, 1, 1, 9, 0, 0),
                clock_out_date=None,
                clock_out_time=None,
                is_supervisor=False,
                pay_rate_override=None
            )
    
    def test_shift_request_validation_invalid_time_range(self):
        """Test that invalid time range raises ValueError."""
        with pytest.raises(ValueError, match="Clock out time must be after clock in time"):
            ShiftRequest(
                employee_name="John Doe",
                clock_in_date=datetime(2024, 1, 1, 17, 0, 0),
                clock_in_time=datetime(2024, 1, 1, 17, 0, 0),
                clock_out_date=datetime(2024, 1, 1, 9, 0, 0),
                clock_out_time=datetime(2024, 1, 1, 9, 0, 0),
                is_supervisor=False,
                pay_rate_override=None
            ) 