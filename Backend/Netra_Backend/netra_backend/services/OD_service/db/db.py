"""
Database configuration and connection management for OD Service.
Centralizes all database-related settings and connection logic.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional


class DatabaseConfig:
    """Database configuration settings."""
    
    def __init__(self):
        """Load database configuration from environment variables."""
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.dbname = os.getenv("DB_NAME", "centraDB")
        self.user = os.getenv("DB_USER", "root")
        self.password = os.getenv("DB_PASSWORD", "root")
    
    def get_connection_params(self) -> dict:
        """Get connection parameters as a dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password
        }


class DatabaseConnection:
    """Manages database connections."""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize database connection manager.
        
        Args:
            config: DatabaseConfig instance. If None, creates a new one.
        """
        self.config = config or DatabaseConfig()
    
    def get_connection(self):
        """
        Establish and return a new database connection.
        
        Returns:
            psycopg2 connection object
            
        Raises:
            Exception: If connection fails
        """
        try:
            conn = psycopg2.connect(**self.config.get_connection_params())
            return conn
        except Exception as e:
            print(f"Error connecting to database: {e}")
            print(f"Connection parameters: host={self.config.host}, "
                  f"port={self.config.port}, dbname={self.config.dbname}, "
                  f"user={self.config.user}")
            raise
    
    def get_cursor(self, conn, dict_cursor: bool = True):
        """
        Get a cursor from the connection.
        
        Args:
            conn: Database connection
            dict_cursor: If True, returns a RealDictCursor. If False, returns normal cursor.
            
        Returns:
            Cursor object
        """
        if dict_cursor:
            return conn.cursor(cursor_factory=RealDictCursor)
        return conn.cursor()


# Table names as constants
class Tables:
    """Database table names."""
    POSITION = "RAW__TLM__EMULATOR__HEALTH_ADCS_SAT_POS_ECEF_FRAME"
    VELOCITY = "RAW__TLM__EMULATOR__HEALTH_ADCS_SAT_VEL_ECEF_FRAME"
    TLE = "tle_data"


# Global database connection instance
_db_connection = None


def get_db_connection():
    """
    Get the global database connection instance.
    Creates a new connection if one doesn't exist.
    
    Returns:
        psycopg2 connection object
    """
    global _db_connection
    if _db_connection is None:
        _db_connection = DatabaseConnection()
    return _db_connection.get_connection()


# Convenience function for backwards compatibility
def get_connection():
    """Alias for get_db_connection()."""
    return get_db_connection()
