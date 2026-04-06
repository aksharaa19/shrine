import os
import json
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

class DatabaseManager:
    def __init__(self):
        self.pool = None
        self._init_pool()
        self._init_tables()
    
    def _init_pool(self):
        db_host = os.environ.get('DB_HOST', 'localhost')
        db_name = os.environ.get('DB_NAME', 'shrine_db')
        db_user = os.environ.get('DB_USER', 'postgres')
        db_password = os.environ.get('DB_PASSWORD', 'postgres')
        db_port = os.environ.get('DB_PORT', '5432')
        
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=db_host,
                database=db_name,
                user=db_user,
                password=db_password,
                port=db_port
            )
            print("Database connection pool created successfully")
        except Exception as e:
            print(f"Failed to create database pool: {e}")
            self.pool = None
    
    def _init_tables(self):
        if not self.pool:
            print("No database pool available, skipping table creation")
            return
        
        conn = self.pool.getconn()
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                role VARCHAR(50) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                token VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_history (
                id SERIAL PRIMARY KEY,
                username VARCHAR(100) NOT NULL,
                video_id VARCHAR(100) NOT NULL,
                video_title TEXT,
                report_data JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id SERIAL PRIMARY KEY,
                video_id VARCHAR(100) NOT NULL,
                comment_id VARCHAR(100),
                author VARCHAR(255),
                text TEXT,
                toxicity_score FLOAT,
                toxicity_level VARCHAR(20),
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cur.close()
        self.pool.putconn(conn)
        print("Database tables initialized")
    
    def execute_query(self, query, params=None, fetch_one=False, fetch_all=False):
        if not self.pool:
            print("No database pool available")
            return None if not fetch_one and not fetch_all else (None if fetch_one else [])
        
        conn = self.pool.getconn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(query, params or [])
            if fetch_one:
                result = cur.fetchone()
            elif fetch_all:
                result = cur.fetchall()
            else:
                conn.commit()
                result = None
            return result
        except Exception as e:
            print(f"Query error: {e}")
            conn.rollback()
            return None if not fetch_one and not fetch_all else (None if fetch_one else [])
        finally:
            cur.close()
            self.pool.putconn(conn)
    
    def close_all(self):
        if self.pool:
            self.pool.closeall()

db_manager = DatabaseManager()