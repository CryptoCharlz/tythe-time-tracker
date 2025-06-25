"""Pytest configuration and fixtures for the time tracking application."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from tythe_time_tracker.core.constants import PayRateType
from tythe_time_tracker.core.models import TimeEntry, TimeSplit
from tythe_time_tracker.database.connection import DatabaseConnection
from tythe_time_tracker.database.repository import TimeEntryRepository
from tythe_time_tracker.core.services import TimeTrackingService


@pytest.fixture
def mock_db_connection():
    """Mock database connection."""
    mock_conn = Mock(spec=DatabaseConnection)
    mock_conn.get_cursor.return_value.__enter__.return_value = Mock()
    mock_conn.get_cursor.return_value.__exit__.return_value = None
    return mock_conn


@pytest.fixture
def mock_repository(mock_db_connection):
    """Mock time entry repository."""
    return Mock(spec=TimeEntryRepository)


@pytest.fixture
def mock_service(mock_repository):
    """Mock time tracking service."""
    return Mock(spec=TimeTrackingService)


@pytest.fixture
def sample_time_entry():
    """Sample time entry for testing."""
    return TimeEntry(
        id="123e4567-e89b-12d3-a456-426614174000",
        employee="John Doe",
        clock_in=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        clock_out=datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc),
        pay_rate_type=PayRateType.STANDARD,
        created_at=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_time_split():
    """Sample time split for testing."""
    return TimeSplit(
        standard_hours=8.0,
        enhanced_hours=0.0,
        supervisor_hours=0.0
    )


@pytest.fixture
def sample_enhanced_time_entry():
    """Sample time entry with enhanced hours for testing."""
    return TimeEntry(
        id="123e4567-e89b-12d3-a456-426614174001",
        employee="Jane Smith",
        clock_in=datetime(2024, 1, 1, 20, 0, 0, tzinfo=timezone.utc),  # 8 PM UTC = 9 PM BST
        clock_out=datetime(2024, 1, 2, 4, 0, 0, tzinfo=timezone.utc),   # 4 AM UTC = 5 AM BST
        pay_rate_type=PayRateType.ENHANCED,
        created_at=datetime(2024, 1, 1, 20, 0, 0, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_supervisor_time_entry():
    """Sample time entry with supervisor rate for testing."""
    return TimeEntry(
        id="123e4567-e89b-12d3-a456-426614174002",
        employee="Manager Bob",
        clock_in=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        clock_out=datetime(2024, 1, 1, 17, 0, 0, tzinfo=timezone.utc),
        pay_rate_type=PayRateType.SUPERVISOR,
        created_at=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_open_time_entry():
    """Sample open time entry (no clock out) for testing."""
    return TimeEntry(
        id="123e4567-e89b-12d3-a456-426614174003",
        employee="Active Worker",
        clock_in=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
        clock_out=None,
        pay_rate_type=PayRateType.STANDARD,
        created_at=datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    )


@pytest.fixture
def sample_time_entries(sample_time_entry, sample_enhanced_time_entry, sample_supervisor_time_entry):
    """Sample list of time entries for testing."""
    return [sample_time_entry, sample_enhanced_time_entry, sample_supervisor_time_entry]


@pytest.fixture
def database_config():
    """Sample database configuration for testing."""
    return {
        "HOST": "test-host",
        "DATABASE": "test-database",
        "USER": "test-user",
        "PASSWORD": "test-password",
        "PORT": 5432
    }


@pytest.fixture
def app_config():
    """Sample application configuration for testing."""
    return {
        "version": "1.0.1",
        "debug": False,
        "log_level": "INFO",
        "manager_password": "test-password"
    } 