#!/usr/bin/env python3
"""Debug script to understand shift splitting issues."""

from datetime import datetime, timezone, timedelta
from export_functions import split_shift_by_rate, get_bst_time

def debug_shift(clock_in, clock_out, description):
    """Debug a specific shift."""
    print(f"\n=== {description} ===")
    print(f"Clock in (UTC): {clock_in}")
    print(f"Clock out (UTC): {clock_out}")
    
    # Convert to BST
    bst_in = get_bst_time(clock_in)
    bst_out = get_bst_time(clock_out)
    print(f"Clock in (BST): {bst_in}")
    print(f"Clock out (BST): {bst_out}")
    
    # Calculate enhanced window
    day = bst_in.date()
    seven_pm = datetime.combine(day, datetime.min.time().replace(hour=19, minute=0))
    four_am_next = datetime.combine(day + timedelta(days=1), datetime.min.time().replace(hour=4, minute=0))
    
    print(f"Enhanced window: {seven_pm} to {four_am_next}")
    
    # Calculate overlap
    enhanced_start = seven_pm
    enhanced_end = four_am_next
    enh_start = max(bst_in.replace(tzinfo=None), enhanced_start)
    enh_end = min(bst_out.replace(tzinfo=None), enhanced_end)
    
    print(f"Enhanced overlap: {enh_start} to {enh_end}")
    
    enhanced_hours = max((enh_end - enh_start).total_seconds() / 3600, 0) if enh_start < enh_end else 0
    total_hours = (bst_out.replace(tzinfo=None) - bst_in.replace(tzinfo=None)).total_seconds() / 3600
    standard_hours = total_hours - enhanced_hours
    
    print(f"Total hours: {total_hours}")
    print(f"Enhanced hours: {enhanced_hours}")
    print(f"Standard hours: {standard_hours}")
    
    result = split_shift_by_rate(clock_in, clock_out, is_supervisor=False)
    print(f"Result: {result}")
    
    return result

# Test case 1: 1:00 AM to 3:00 AM BST (should be all enhanced)
clock_in1 = datetime(2025, 6, 26, 0, 0, tzinfo=timezone.utc)   # 1:00 BST
clock_out1 = datetime(2025, 6, 26, 2, 0, tzinfo=timezone.utc)   # 3:00 BST
debug_shift(clock_in1, clock_out1, "Night shift (1:00 AM - 3:00 AM BST)")

# Test case 2: 3:00 AM to 7:00 AM BST (should be 1h enhanced + 3h standard)
clock_in2 = datetime(2025, 6, 26, 2, 0, tzinfo=timezone.utc)   # 3:00 BST
clock_out2 = datetime(2025, 6, 26, 6, 0, tzinfo=timezone.utc)   # 7:00 BST
debug_shift(clock_in2, clock_out2, "Morning shift (3:00 AM - 7:00 AM BST)") 