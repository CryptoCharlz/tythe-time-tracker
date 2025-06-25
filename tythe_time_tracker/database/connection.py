"""Database connection management for the time tracking application."""

import logging
from contextlib import contextmanager
from typing import Optional

import psycopg2
from psycopg2.extensions import connection
from psycopg2.pool import SimpleConnectionPool

from ..core.constants import DatabaseConstants, ErrorMessages, PayRateType

logger = logging.getLogger(__name__)


def get_db_connection() -> Optional[connection]:
    """Create and return a database connection using Streamlit secrets.
    
    Returns:
        Database connection if successful, None otherwise.
    """
    try:
        import streamlit as st
        
        conn = psycopg2.connect(
            host=st.secrets["SUPABASE"]["HOST"],
            database=st.secrets["SUPABASE"]["DATABASE"],
            user=st.secrets["SUPABASE"]["USER"],
            password=st.secrets["SUPABASE"]["PASSWORD"],
            port=st.secrets["SUPABASE"]["PORT"],
            # Force IPv4 connection to avoid IPv6 issues
            options='-c family=ipv4'
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


class DatabaseConnection:
    """Manages database connections and provides connection pooling."""
    
    def __init__(self, db_connection: connection) -> None:
        """Initialize the database connection manager.
        
        Args:
            db_connection: An existing database connection.
        """
        self.connection = db_connection
    
    def get_connection(self) -> connection:
        """Get the database connection.
        
        Returns:
            The database connection.
        """
        return self.connection
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations.
        
        Yields:
            A database cursor for executing queries.
            
        Raises:
            ConnectionError: If database connection fails.
        """
        cursor = None
        try:
            cursor = self.connection.cursor()
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def close(self) -> None:
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
    
    def test_connection(self) -> bool:
        """Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise.
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def initialize_tables(self) -> None:
        """Initialize database tables if they don't exist."""
        try:
            with self.get_cursor() as cursor:
                # Create time_entries table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {DatabaseConstants.TIME_ENTRIES_TABLE} (
                        {DatabaseConstants.ID_COLUMN} UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        {DatabaseConstants.EMPLOYEE_COLUMN} TEXT NOT NULL,
                        {DatabaseConstants.CLOCK_IN_COLUMN} TIMESTAMPTZ NOT NULL,
                        {DatabaseConstants.CLOCK_OUT_COLUMN} TIMESTAMPTZ,
                        {DatabaseConstants.PAY_RATE_TYPE_COLUMN} TEXT DEFAULT '{PayRateType.STANDARD}',
                        {DatabaseConstants.CREATED_AT_COLUMN} TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
                
                # Check if pay_rate_type column exists, add if not
                cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{DatabaseConstants.TIME_ENTRIES_TABLE}' 
                    AND column_name = '{DatabaseConstants.PAY_RATE_TYPE_COLUMN}'
                """)
                
                if not cursor.fetchone():
                    cursor.execute(f"""
                        ALTER TABLE {DatabaseConstants.TIME_ENTRIES_TABLE} 
                        ADD COLUMN {DatabaseConstants.PAY_RATE_TYPE_COLUMN} TEXT DEFAULT '{PayRateType.STANDARD}'
                    """)
                    logger.info("Database updated with pay rate functionality")
                
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database tables: {e}")
            raise RuntimeError(ErrorMessages.DB_INIT_FAILED) from e 