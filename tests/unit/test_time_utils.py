"""Unit tests for time utility functions."""

import pytest
from datetime import datetime, timezone, timedelta

from tythe_time_tracker.utils.time_utils import TimeUtils
from tythe_time_tracker.core.constants import TimeConstants
from export_functions import split_shift_by_rate, get_bst_time


class TestTimeUtils:
    """Test TimeUtils class."""
    
    def test_convert_to_bst_with_utc_time(self):
        """Test converting UTC time to BST."""
        utc_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        bst_time = TimeUtils.convert_to_bst(utc_time)
        
        expected_bst = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        assert bst_time == expected_bst
    
    def test_convert_to_bst_with_naive_time(self):
        """Test converting naive time to BST (assumes UTC)."""
        naive_time = datetime(2024, 1, 1, 12, 0, 0)
        bst_time = TimeUtils.convert_to_bst(naive_time)
        
        expected_bst = datetime(2024, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
        assert bst_time == expected_bst
    
    def test_convert_to_utc_with_naive_time(self):
        """Test converting naive time to UTC."""
        naive_time = datetime(2024, 1, 1, 12, 0, 0)
        utc_time = TimeUtils.convert_to_utc(naive_time)
        
        expected_utc = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert utc_time == expected_utc
    
    def test_convert_to_utc_with_utc_time(self):
        """Test converting UTC time to UTC (no change)."""
        utc_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = TimeUtils.convert_to_utc(utc_time)
        
        assert result == utc_time
    
    def test_is_enhanced_hours_standard_time(self):
        """Test that standard hours return False."""
        # 2 PM UTC = 3 PM BST (standard hours)
        standard_time = datetime(2024, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        assert not TimeUtils.is_enhanced_hours(standard_time)
    
    def test_is_enhanced_hours_enhanced_time_evening(self):
        """Test that evening enhanced hours return True."""
        # 8 PM UTC = 9 PM BST (enhanced hours)
        enhanced_time = datetime(2024, 1, 1, 20, 0, 0, tzinfo=timezone.utc)
        assert TimeUtils.is_enhanced_hours(enhanced_time)
    
    def test_is_enhanced_hours_enhanced_time_night(self):
        """Test that night enhanced hours return True."""
        # 2 AM UTC = 3 AM BST (enhanced hours)
        enhanced_time = datetime(2024, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
        assert TimeUtils.is_enhanced_hours(enhanced_time)
    
    def test_is_enhanced_hours_boundary_times(self):
        """Test boundary times for enhanced hours."""
        # 7 PM BST boundary (should be enhanced)
        seven_pm_bst = datetime(2024, 1, 1, 18, 0, 0, tzinfo=timezone.utc)  # 7 PM UTC = 8 PM BST
        assert TimeUtils.is_enhanced_hours(seven_pm_bst)
        
        # 3:59 AM BST boundary (should be enhanced)
        three_fifty_nine_bst = datetime(2024, 1, 1, 2, 59, 0, tzinfo=timezone.utc)  # 2:59 UTC = 3:59 BST
        assert TimeUtils.is_enhanced_hours(three_fifty_nine_bst)
        
        # 4 AM BST boundary (should be standard)
        four_am_bst_standard = datetime(2024, 1, 1, 3, 0, 0, tzinfo=timezone.utc)  # 3:00 UTC = 4:00 BST
        assert not TimeUtils.is_enhanced_hours(four_am_bst_standard)
    
    def test_format_duration_with_end_time(self):
        """Test formatting duration with end time."""
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 17, 30, 45, tzinfo=timezone.utc)
        
        duration = TimeUtils.format_duration(start_time, end_time)
        assert duration == "08:30:45"
    
    def test_format_duration_without_end_time(self):
        """Test formatting duration without end time."""
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        
        duration = TimeUtils.format_duration(start_time, None)
        assert duration == "In Progress"
    
    def test_format_duration_short_duration(self):
        """Test formatting short duration (less than 1 hour)."""
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 9, 30, 15, tzinfo=timezone.utc)
        
        duration = TimeUtils.format_duration(start_time, end_time)
        assert duration == "30:15"
    
    def test_round_hours(self):
        """Test rounding hours to specified precision."""
        hours = 8.123456
        rounded = TimeUtils.round_hours(hours)
        assert rounded == 8.12  # Should round to 2 decimal places
    
    def test_get_current_utc_time(self):
        """Test getting current UTC time."""
        current_time = TimeUtils.get_current_utc_time()
        
        assert current_time.tzinfo == timezone.utc
        assert isinstance(current_time, datetime)
        
        # Should be close to now (within 1 second)
        now = datetime.now(timezone.utc)
        time_diff = abs((current_time - now).total_seconds())
        assert time_diff < 1
    
    def test_get_current_bst_time(self):
        """Test getting current BST time."""
        bst_time = TimeUtils.get_current_bst_time()
        
        assert bst_time.tzinfo == timezone.utc
        assert isinstance(bst_time, datetime)
        
        # Should be 1 hour ahead of UTC
        utc_time = TimeUtils.get_current_utc_time()
        time_diff = (bst_time - utc_time).total_seconds()
        assert abs(time_diff - 3600) < 1  # Within 1 second of 1 hour
    
    def test_is_valid_time_range_valid(self):
        """Test valid time range."""
        start_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
        
        assert TimeUtils.is_valid_time_range(start_time, end_time)
    
    def test_is_valid_time_range_invalid(self):
        """Test invalid time range."""
        start_time = datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        
        assert not TimeUtils.is_valid_time_range(start_time, end_time)
    
    def test_is_valid_time_range_same_time(self):
        """Test time range with same start and end time."""
        time = datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        
        assert not TimeUtils.is_valid_time_range(time, time)
    
    def test_parse_time_string_valid_formats(self):
        """Test parsing valid time string formats."""
        # Test different formats
        test_cases = [
            ("2024-01-01 09:00:00", datetime(2024, 1, 1, 9, 0, 0)),
            ("2024-01-01 09:00", datetime(2024, 1, 1, 9, 0)),
            ("09:00:00", datetime(1900, 1, 1, 9, 0, 0)),
            ("09:00", datetime(1900, 1, 1, 9, 0))
        ]
        
        for time_str, expected in test_cases:
            result = TimeUtils.parse_time_string(time_str)
            assert result == expected
    
    def test_parse_time_string_invalid_format(self):
        """Test parsing invalid time string format."""
        invalid_time = "invalid-time"
        result = TimeUtils.parse_time_string(invalid_time)
        assert result is None
    
    def test_parse_time_string_empty_string(self):
        """Test parsing empty time string."""
        result = TimeUtils.parse_time_string("")
        assert result is None
    
    def test_split_shift_by_rate_overnight(self):
        """Test that an overnight shift is split correctly between enhanced and standard hours."""
        # Shift: 23:44 to 07:45 BST (assume BST, so input as UTC)
        # 23:44 BST = 22:44 UTC, 07:45 BST = 06:45 UTC
        from datetime import datetime, timezone, timedelta
        clock_in = datetime(2025, 6, 25, 22, 44, tzinfo=timezone.utc)  # 23:44 BST
        clock_out = datetime(2025, 6, 26, 6, 45, tzinfo=timezone.utc)  # 07:45 BST
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        # Enhanced: 23:44–04:00 (4:00 BST = 3:00 UTC next day)
        enhanced_end = datetime(2025, 6, 26, 3, 0, tzinfo=timezone.utc)  # 04:00 BST
        enhanced_hours = (enhanced_end - clock_in).total_seconds() / 3600
        # Standard: 04:00–07:45
        standard_hours = (clock_out - enhanced_end).total_seconds() / 3600
        assert abs(result['Enhanced'] - round(enhanced_hours, 2)) < 0.01, f"Enhanced hours wrong: {result['Enhanced']} != {round(enhanced_hours, 2)}"
        assert abs(result['Standard'] - round(standard_hours, 2)) < 0.01, f"Standard hours wrong: {result['Standard']} != {round(standard_hours, 2)}"
        assert result['Supervisor'] == 0 