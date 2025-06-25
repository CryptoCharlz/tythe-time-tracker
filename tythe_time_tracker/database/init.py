"""
Database initialization module.

This module handles the setup and initialization of database tables.
"""

import logging
from typing import Optional

from .connection import get_db_connection
from .connection import DatabaseConnection
from ..core.constants import DatabaseConstants

logger = logging.getLogger(__name__)


def init_database() -> bool:
    """Initialize the database tables if they don't exist.
    
    Returns:
        True if initialization was successful, False otherwise.
    """
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to establish database connection")
            return False
        
        db = DatabaseConnection(conn)
        
        with db.get_cursor() as cursor:
            # Create time_entries table if it doesn't exist
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {DatabaseConstants.TIME_ENTRIES_TABLE} (
                    {DatabaseConstants.ID_COLUMN} UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    {DatabaseConstants.EMPLOYEE_COLUMN} TEXT NOT NULL,
                    {DatabaseConstants.CLOCK_IN_COLUMN} TIMESTAMPTZ NOT NULL,
                    {DatabaseConstants.CLOCK_OUT_COLUMN} TIMESTAMPTZ,
                    {DatabaseConstants.PAY_RATE_TYPE_COLUMN} TEXT DEFAULT '{DatabaseConstants.DEFAULT_PAY_RATE}',
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
                    ADD COLUMN {DatabaseConstants.PAY_RATE_TYPE_COLUMN} TEXT DEFAULT '{DatabaseConstants.DEFAULT_PAY_RATE}'
                """)
                logger.info("Database updated with pay rate functionality")
        
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def ensure_database_ready() -> bool:
    """Ensure the database is ready for use.
    
    This function initializes the database if needed and returns
    whether the database is ready for operations.
    
    Returns:
        True if database is ready, False otherwise.
    """
    return init_database() 