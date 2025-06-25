"""The Tythe Barn Time Tracker Application."""

__version__ = "1.0.1"
__author__ = "The Tythe Barn Team"
__description__ = "A time tracking application for The Tythe Barn"

from .core.models import TimeEntry, PayRateType
from .core.services import TimeTrackingService
from .database.connection import DatabaseConnection

__all__ = [
    "__version__",
    "__author__",
    "__description__",
    "TimeEntry",
    "PayRateType", 
    "TimeTrackingService",
    "DatabaseConnection",
] 