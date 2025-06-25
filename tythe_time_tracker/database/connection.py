"""Database connection management for the time tracking application."""

import logging
from contextlib import contextmanager
from typing import Optional

import psycopg2
from psycopg2.extensions import connection
from psycopg2.pool import SimpleConnectionPool

from ..core.constants import DatabaseConstants, ErrorMessages, PayRateType

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages database connections and provides connection pooling."""
    
    def __init__(self, config: dict) -> None:
        """Initialize the database connection manager.
        
        Args:
            config: Database configuration dictionary containing:
                - HOST: Database host
                - DATABASE: Database name
                - USER: Database user
                - PASSWORD: Database password
                - PORT: Database port
        """
        self.config = config
        self._pool: Optional[SimpleConnectionPool] = None
        self._min_connections = 1
        self._max_connections = 10
    
    def initialize_pool(self) -> None:
        """Initialize the connection pool."""
        try:
            self._pool = SimpleConnectionPool(
                minconn=self._min_connections,
                maxconn=self._max_connections,
                host=self.config["HOST"],
                database=self.config["DATABASE"],
                user=self.config["USER"],
                password=self.config["PASSWORD"],
                port=self.config["PORT"],
                options='-c family=ipv4'
            )
            logger.info("Database connection pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise ConnectionError(ErrorMessages.DB_CONNECTION_FAILED) from e
    
    def get_connection(self) -> connection:
        """Get a connection from the pool.
        
        Returns:
            A database connection from the pool.
            
        Raises:
            ConnectionError: If the pool is not initialized or no connections available.
        """
        if not self._pool:
            self.initialize_pool()
        
        try:
            return self._pool.getconn()
        except Exception as e:
            logger.error(f"Failed to get database connection: {e}")
            raise ConnectionError(ErrorMessages.DB_CONNECTION_FAILED) from e
    
    def return_connection(self, conn: connection) -> None:
        """Return a connection to the pool.
        
        Args:
            conn: The database connection to return.
        """
        if self._pool:
            try:
                self._pool.putconn(conn)
            except Exception as e:
                logger.error(f"Failed to return database connection: {e}")
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations.
        
        Yields:
            A database cursor for executing queries.
            
        Raises:
            ConnectionError: If database connection fails.
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                self.return_connection(conn)
    
    def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")
    
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