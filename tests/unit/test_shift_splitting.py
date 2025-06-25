"""Comprehensive tests for shift splitting logic."""

import pytest
from datetime import datetime, timezone, timedelta
from export_functions import split_shift_by_rate


class TestShiftSplitting:
    """Test all possible shift splitting scenarios."""
    
    def test_standard_shift_only(self):
        """Test a shift that's entirely within standard hours (4:00 AM - 7:00 PM BST)."""
        # 9:00 AM to 5:00 PM BST
        clock_in = datetime(2025, 6, 25, 8, 0, tzinfo=timezone.utc)   # 9:00 BST
        clock_out = datetime(2025, 6, 25, 16, 0, tzinfo=timezone.utc) # 17:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        assert result['Standard'] == 8.0
        assert result['Enhanced'] == 0.0
        assert result['Supervisor'] == 0.0
    
    def test_enhanced_shift_only_evening(self):
        """Test a shift that's entirely within enhanced hours (7:00 PM - 4:00 AM BST)."""
        # 8:00 PM to 11:00 PM BST
        clock_in = datetime(2025, 6, 25, 19, 0, tzinfo=timezone.utc)  # 20:00 BST
        clock_out = datetime(2025, 6, 25, 22, 0, tzinfo=timezone.utc)  # 23:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        assert result['Standard'] == 0.0
        assert result['Enhanced'] == 3.0
        assert result['Supervisor'] == 0.0
    
    def test_enhanced_shift_only_night(self):
        """Test a shift that's entirely within enhanced hours (night)."""
        # 1:00 AM to 3:00 AM BST
        clock_in = datetime(2025, 6, 26, 0, 0, tzinfo=timezone.utc)   # 1:00 BST
        clock_out = datetime(2025, 6, 26, 2, 0, tzinfo=timezone.utc)   # 3:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        assert result['Standard'] == 0.0
        assert result['Enhanced'] == 2.0
        assert result['Supervisor'] == 0.0
    
    def test_shift_standard_to_enhanced(self):
        """Test a shift that starts in standard hours and goes into enhanced hours."""
        # 5:00 PM to 9:00 PM BST (crosses 7:00 PM boundary)
        clock_in = datetime(2025, 6, 25, 16, 0, tzinfo=timezone.utc)  # 17:00 BST
        clock_out = datetime(2025, 6, 25, 20, 0, tzinfo=timezone.utc)  # 21:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        # Standard: 17:00-19:00 (2 hours)
        # Enhanced: 19:00-21:00 (2 hours)
        assert result['Standard'] == 2.0
        assert result['Enhanced'] == 2.0
        assert result['Supervisor'] == 0.0
    
    def test_shift_enhanced_to_standard(self):
        """Test a shift that starts in enhanced hours and goes into standard hours."""
        # 3:00 AM to 7:00 AM BST (crosses 4:00 AM boundary)
        clock_in = datetime(2025, 6, 26, 2, 0, tzinfo=timezone.utc)   # 3:00 BST
        clock_out = datetime(2025, 6, 26, 6, 0, tzinfo=timezone.utc)   # 7:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        # Enhanced: 3:00-4:00 (1 hour)
        # Standard: 4:00-7:00 (3 hours)
        assert result['Standard'] == 3.0
        assert result['Enhanced'] == 1.0
        assert result['Supervisor'] == 0.0
    
    def test_overnight_shift_enhanced_to_standard(self):
        """Test a full overnight shift from enhanced to standard hours."""
        # 11:00 PM to 6:00 AM BST (overnight)
        clock_in = datetime(2025, 6, 25, 22, 0, tzinfo=timezone.utc)  # 23:00 BST
        clock_out = datetime(2025, 6, 26, 5, 0, tzinfo=timezone.utc)   # 6:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        # Enhanced: 23:00-4:00 (5 hours)
        # Standard: 4:00-6:00 (2 hours)
        assert result['Standard'] == 2.0
        assert result['Enhanced'] == 5.0
        assert result['Supervisor'] == 0.0
    
    def test_overnight_shift_standard_to_enhanced(self):
        """Test a shift that starts in standard hours, goes through enhanced, and ends in standard."""
        # 6:00 PM to 6:00 AM BST (overnight)
        clock_in = datetime(2025, 6, 25, 17, 0, tzinfo=timezone.utc)  # 18:00 BST
        clock_out = datetime(2025, 6, 26, 5, 0, tzinfo=timezone.utc)   # 6:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        # Standard: 18:00-19:00 (1 hour)
        # Enhanced: 19:00-4:00 (9 hours)
        # Standard: 4:00-6:00 (2 hours)
        assert result['Standard'] == 3.0  # 1 + 2
        assert result['Enhanced'] == 9.0
        assert result['Supervisor'] == 0.0
    
    def test_boundary_times_exact(self):
        """Test shifts that start/end exactly on boundaries."""
        # 7:00 PM to 4:00 AM BST (exact boundaries)
        clock_in = datetime(2025, 6, 25, 18, 0, tzinfo=timezone.utc)  # 19:00 BST
        clock_out = datetime(2025, 6, 26, 3, 0, tzinfo=timezone.utc)   # 4:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        # Enhanced: 19:00-4:00 (9 hours)
        assert result['Standard'] == 0.0
        assert result['Enhanced'] == 9.0
        assert result['Supervisor'] == 0.0
    
    def test_boundary_times_just_before(self):
        """Test shifts that end just before boundaries."""
        # 6:00 PM to 6:59 PM BST (just before enhanced)
        clock_in = datetime(2025, 6, 25, 17, 0, tzinfo=timezone.utc)  # 18:00 BST
        clock_out = datetime(2025, 6, 25, 17, 59, tzinfo=timezone.utc) # 18:59 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        assert result['Standard'] == pytest.approx(0.98, abs=0.01)  # 59 minutes
        assert result['Enhanced'] == 0.0
        assert result['Supervisor'] == 0.0
    
    def test_boundary_times_just_after(self):
        """Test shifts that start just after boundaries."""
        # 7:01 PM to 8:00 PM BST (just after enhanced starts)
        clock_in = datetime(2025, 6, 25, 18, 1, tzinfo=timezone.utc)  # 19:01 BST
        clock_out = datetime(2025, 6, 25, 19, 0, tzinfo=timezone.utc)  # 20:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        assert result['Standard'] == 0.0
        assert result['Enhanced'] == pytest.approx(0.98, abs=0.01)  # 59 minutes
        assert result['Supervisor'] == 0.0
    
    def test_supervisor_shift(self):
        """Test that supervisor shifts get all hours as supervisor."""
        # 9:00 AM to 5:00 PM BST
        clock_in = datetime(2025, 6, 25, 8, 0, tzinfo=timezone.utc)   # 9:00 BST
        clock_out = datetime(2025, 6, 25, 16, 0, tzinfo=timezone.utc) # 17:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=True)
        
        assert result['Standard'] == 0.0
        assert result['Enhanced'] == 0.0
        assert result['Supervisor'] == 8.0
    
    def test_open_shift(self):
        """Test that open shifts (no clock out) return zero hours."""
        clock_in = datetime(2025, 6, 25, 8, 0, tzinfo=timezone.utc)   # 9:00 BST
        clock_out = None
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        assert result['Standard'] == 0.0
        assert result['Enhanced'] == 0.0
        assert result['Supervisor'] == 0.0
    
    def test_invalid_shift(self):
        """Test that invalid shifts (clock out before clock in) return zero hours."""
        clock_in = datetime(2025, 6, 25, 16, 0, tzinfo=timezone.utc)  # 17:00 BST
        clock_out = datetime(2025, 6, 25, 8, 0, tzinfo=timezone.utc)   # 9:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        assert result['Standard'] == 0.0
        assert result['Enhanced'] == 0.0
        assert result['Supervisor'] == 0.0
    
    def test_very_short_shift(self):
        """Test a very short shift (30 minutes)."""
        # 6:30 PM to 7:00 PM BST (crosses boundary)
        clock_in = datetime(2025, 6, 25, 17, 30, tzinfo=timezone.utc) # 18:30 BST
        clock_out = datetime(2025, 6, 25, 18, 0, tzinfo=timezone.utc)  # 19:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        # Standard: 18:30-19:00 (0.5 hours)
        assert result['Standard'] == 0.5
        assert result['Enhanced'] == 0.0
        assert result['Supervisor'] == 0.0
    
    def test_very_long_overnight_shift(self):
        """Test a very long overnight shift (16 hours)."""
        # 4:00 PM to 8:00 AM BST (16 hours, overnight)
        clock_in = datetime(2025, 6, 25, 15, 0, tzinfo=timezone.utc)  # 16:00 BST
        clock_out = datetime(2025, 6, 26, 7, 0, tzinfo=timezone.utc)   # 8:00 BST
        
        result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
        
        # Standard: 16:00-19:00 (3 hours) + 4:00-8:00 (4 hours) = 7 hours
        # Enhanced: 19:00-4:00 (9 hours)
        assert result['Standard'] == 7.0
        assert result['Enhanced'] == 9.0
        assert result['Supervisor'] == 0.0
        assert result['Standard'] + result['Enhanced'] == 16.0  # Total should be 16 hours 