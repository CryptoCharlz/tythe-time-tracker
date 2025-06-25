"""Time utility functions for the time tracking application."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from ..core.constants import TimeConstants


class TimeUtils:
    """Utility class for time-related operations."""
    
    @staticmethod
    def convert_to_bst(utc_time: datetime) -> datetime:
        """Convert UTC time to BST (British Summer Time).
        
        Args:
            utc_time: UTC datetime to convert.
            
        Returns:
            BST datetime.
        """
        if utc_time.tzinfo is None:
            # Assume it's UTC if no timezone info
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        
        bst_offset = timedelta(hours=TimeConstants.BST_OFFSET_HOURS)
        return utc_time + bst_offset
    
    @staticmethod
    def convert_to_utc(local_time: datetime) -> datetime:
        """Convert local time to UTC.
        
        Args:
            local_time: Local datetime to convert.
            
        Returns:
            UTC datetime.
        """
        if local_time.tzinfo is None:
            # Assume it's local time and convert to UTC
            # This is a simplified conversion - in production you might want more sophisticated handling
            local_time = local_time.replace(tzinfo=timezone.utc)
        
        return local_time.astimezone(timezone.utc)
    
    @staticmethod
    def is_enhanced_hours(clock_in_time: datetime) -> bool:
        """Check if clock-in time is during enhanced hours in BST.
        
        Args:
            clock_in_time: Clock-in time to check.
            
        Returns:
            True if during enhanced hours, False otherwise.
        """
        # Convert to BST if it's UTC
        if clock_in_time.tzinfo is None:
            # Assume it's UTC if no timezone info
            clock_in_time = clock_in_time.replace(tzinfo=timezone.utc)
        
        bst_time = TimeUtils.convert_to_bst(clock_in_time)
        hour = bst_time.hour
        
        # Enhanced rate: 7:00 PM (19:00) to 4:00 AM (04:00) in BST
        return hour >= TimeConstants.ENHANCED_START_HOUR or hour < TimeConstants.ENHANCED_END_HOUR
    
    @staticmethod
    def format_duration(start_time: datetime, end_time: Optional[datetime]) -> str:
        """Format duration between two times.
        
        Args:
            start_time: Start time.
            end_time: End time (optional).
            
        Returns:
            Formatted duration string.
        """
        if not end_time:
            return "In Progress"
        
        duration = end_time - start_time
        total_seconds = int(duration.total_seconds())
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def round_hours(hours: float) -> float:
        """Round hours to the specified precision.
        
        Args:
            hours: Hours to round.
            
        Returns:
            Rounded hours.
        """
        return round(hours, TimeConstants.HOURS_PRECISION)
    
    @staticmethod
    def get_current_utc_time() -> datetime:
        """Get current UTC time.
        
        Returns:
            Current UTC datetime.
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def get_current_bst_time() -> datetime:
        """Get current BST time.
        
        Returns:
            Current BST datetime.
        """
        return TimeUtils.convert_to_bst(TimeUtils.get_current_utc_time())
    
    @staticmethod
    def is_valid_time_range(start_time: datetime, end_time: datetime) -> bool:
        """Check if a time range is valid.
        
        Args:
            start_time: Start time.
            end_time: End time.
            
        Returns:
            True if valid, False otherwise.
        """
        return end_time > start_time
    
    @staticmethod
    def parse_time_string(time_str: str) -> Optional[datetime]:
        """Parse a time string to datetime.
        
        Args:
            time_str: Time string to parse.
            
        Returns:
            Parsed datetime or None if invalid.
        """
        try:
            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%H:%M:%S",
                "%H:%M"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_str, fmt)
                except ValueError:
                    continue
            
            return None
        except Exception:
            return None 