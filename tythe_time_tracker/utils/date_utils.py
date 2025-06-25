"""Date utility functions for the time tracking application."""

from datetime import date, datetime, timedelta
from typing import Optional, Tuple

from ..core.constants import UIConstants


class DateUtils:
    """Utility class for date-related operations."""
    
    @staticmethod
    def get_date_range(option: str) -> Tuple[Optional[date], Optional[date]]:
        """Get date range based on selection.
        
        Args:
            option: Date range option (This Week, Last Week, This Month, etc.).
            
        Returns:
            Tuple of (start_date, end_date).
        """
        today = datetime.now().date()
        
        if option == UIConstants.THIS_WEEK:
            # Monday to Sunday
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
        elif option == UIConstants.LAST_WEEK:
            # Previous Monday to Sunday
            start = today - timedelta(days=today.weekday() + 7)
            end = start + timedelta(days=6)
        elif option == UIConstants.THIS_MONTH:
            # First to last day of current month
            start = today.replace(day=1)
            if today.month == 12:
                end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        else:  # Custom range
            return None, None
        
        return start, end
    
    @staticmethod
    def get_current_month_range() -> Tuple[date, date]:
        """Get the current month date range.
        
        Returns:
            Tuple of (first_day_of_month, last_day_of_month).
        """
        today = datetime.now().date()
        start = today.replace(day=1)
        
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        
        return start, end
    
    @staticmethod
    def get_week_range(target_date: date) -> Tuple[date, date]:
        """Get the week range for a given date.
        
        Args:
            target_date: Date to get week range for.
            
        Returns:
            Tuple of (monday, sunday).
        """
        monday = target_date - timedelta(days=target_date.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday
    
    @staticmethod
    def get_previous_week_range(target_date: date) -> Tuple[date, date]:
        """Get the previous week range for a given date.
        
        Args:
            target_date: Date to get previous week range for.
            
        Returns:
            Tuple of (previous_monday, previous_sunday).
        """
        monday = target_date - timedelta(days=target_date.weekday() + 7)
        sunday = monday + timedelta(days=6)
        return monday, sunday
    
    @staticmethod
    def is_valid_date_range(start_date: date, end_date: date) -> bool:
        """Check if a date range is valid.
        
        Args:
            start_date: Start date.
            end_date: End date.
            
        Returns:
            True if valid, False otherwise.
        """
        return end_date >= start_date
    
    @staticmethod
    def format_date_range(start_date: date, end_date: date) -> str:
        """Format a date range as a string.
        
        Args:
            start_date: Start date.
            end_date: End date.
            
        Returns:
            Formatted date range string.
        """
        if start_date == end_date:
            return start_date.strftime("%Y-%m-%d")
        else:
            return f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    
    @staticmethod
    def get_date_options() -> list[str]:
        """Get available date range options.
        
        Returns:
            List of date range option strings.
        """
        return [
            UIConstants.CUSTOM_RANGE,
            UIConstants.THIS_WEEK,
            UIConstants.LAST_WEEK,
            UIConstants.THIS_MONTH
        ]
    
    @staticmethod
    def parse_date_string(date_str: str) -> Optional[date]:
        """Parse a date string to date object.
        
        Args:
            date_str: Date string to parse.
            
        Returns:
            Parsed date or None if invalid.
        """
        try:
            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%m/%d/%Y",
                "%Y-%m-%d %H:%M:%S"
            ]
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    return parsed.date()
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None 