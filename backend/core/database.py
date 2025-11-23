# """
# Database Operations - Complete CRUD with proper error handling
# """

# import psycopg2
# from psycopg2.extras import RealDictCursor
# import os
# from dotenv import load_dotenv
# from contextlib import contextmanager

# load_dotenv()

# def get_db_config():
#     """Get database configuration from environment"""
#     database_url = os.getenv('DATABASE_URL')
    
#     if database_url:
#         # Parse Railway/Heroku style DATABASE_URL
#         # Format: postgresql://user:password@host:port/database
#         url = urlparse(database_url)
        
#         return {
#             'host': url.hostname,
#             'port': url.port or 5432,
#             'database': url.path[1:],  # Remove leading '/'
#             'user': url.username,
#             'password': url.password
#         }
#     else:
#         # Use individual env vars (local development)
#         return {
#             'host': os.getenv('DB_HOST', 'localhost'),
#             'port': int(os.getenv('DB_PORT', 5432)),
#             'database': os.getenv('DB_NAME', 'chatfinance_db'),
#             'user': os.getenv('DB_USER', 'postgres'),
#             'password': os.getenv('DB_PASSWORD', '')
#         }


# @contextmanager
# def get_db_connection():
#     """Context manager for database connections"""
#     conn = None
#     try:
#         conn = psycopg2.connect(
#             host=os.getenv('DB_HOST', 'localhost'),
#             port=os.getenv('DB_PORT', '5432'),
#             database=os.getenv('DB_NAME', 'chatfinance_db'),
#             user=os.getenv('DB_USER', 'chatfinance_user'),
#             password=os.getenv('DB_PASSWORD', 'chatfinance123')
#         )
#         yield conn
#         conn.commit()
#     except Exception as e:
#         if conn:
#             conn.rollback()
#         raise e
#     finally:
#         if conn:
#             conn.close()


# class DatabaseOperations:
#     """Database operations for ChatFinance-AI"""
    
#     @staticmethod
#     def execute_query(query, params=None, fetch=True):
#         """Execute a query and return results"""
#         try:
#             with get_db_connection() as conn:
#                 with conn.cursor(cursor_factory=RealDictCursor) as cursor:
#                     cursor.execute(query, params or ())
#                     if fetch:
#                         return cursor.fetchall()
#                     return cursor.rowcount
#         except Exception as e:
#             print(f"Database error: {str(e)}")
#             return [] if fetch else 0
    
#     @staticmethod
#     def initialize_database():
#         """Initialize database with schema"""
#         try:
#             schema_path = os.path.join('sql', 'schema.sql')
            
#             if not os.path.exists(schema_path):
#                 print(f"⚠️ Schema file not found at: {schema_path}")
#                 print("Creating tables manually...")
                
#                 with get_db_connection() as conn:
#                     with conn.cursor() as cursor:
#                         cursor.execute("""
#                             CREATE TABLE IF NOT EXISTS users (
#                                 id SERIAL PRIMARY KEY,
#                                 username VARCHAR(50) UNIQUE NOT NULL,
#                                 email VARCHAR(255) UNIQUE NOT NULL,
#                                 password_hash TEXT NOT NULL,
#                                 full_name VARCHAR(100) NOT NULL,
#                                 role VARCHAR(20) DEFAULT 'user',
#                                 is_active BOOLEAN DEFAULT TRUE,
#                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                                 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#                                 last_login TIMESTAMP
#                             );
                            
#                             CREATE TABLE IF NOT EXISTS ocr_documents (
#                                 id SERIAL PRIMARY KEY,
#                                 filename VARCHAR(255) NOT NULL,
#                                 file_path TEXT,
#                                 extracted_text TEXT,
#                                 confidence_score DECIMAL(5, 2),
#                                 processing_time DECIMAL(8, 2),
#                                 ocr_engine VARCHAR(50),
#                                 uploaded_by INTEGER REFERENCES users(id),
#                                 payment_status VARCHAR(20) DEFAULT 'unpaid',
#                                 payment_date TIMESTAMP,
#                                 due_date DATE,
#                                 reminder_date DATE,
#                                 reminder_sent BOOLEAN DEFAULT FALSE,
#                                 amount DECIMAL(10, 2),
#                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                             );
                            
#                             CREATE TABLE IF NOT EXISTS document_categories (
#                                 id SERIAL PRIMARY KEY,
#                                 document_id INTEGER REFERENCES ocr_documents(id) ON DELETE CASCADE,
#                                 category VARCHAR(100) NOT NULL,
#                                 confidence DECIMAL(5, 2),
#                                 metadata JSONB,
#                                 verified BOOLEAN DEFAULT FALSE,
#                                 verified_by INTEGER,
#                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                             );
                            
#                             CREATE TABLE IF NOT EXISTS audit_log (
#                                 id SERIAL PRIMARY KEY,
#                                 user_id INTEGER,
#                                 action VARCHAR(100) NOT NULL,
#                                 table_name VARCHAR(50),
#                                 record_id INTEGER,
#                                 old_values JSONB,
#                                 new_values JSONB,
#                                 ip_address INET,
#                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#                             );
#                         """)
#                 print("✅ Essential tables created")
#                 return True
            
#             with open(schema_path, 'r', encoding='utf-8') as f:
#                 schema_sql = f.read()
            
#             with get_db_connection() as conn:
#                 with conn.cursor() as cursor:
#                     cursor.execute(schema_sql)
            
#             print("✅ Database initialized successfully")
#             return True
#         except Exception as e:
#             print(f"❌ Database initialization failed: {str(e)}")
#             return False
    
#     @staticmethod
#     def save_ocr_document(filename, file_path, extracted_text, confidence_score,
#                          processing_time, ocr_engine, uploaded_by):
#         """Save OCR document"""
#         try:
#             query = """
#                 INSERT INTO ocr_documents 
#                 (filename, file_path, extracted_text, confidence_score, 
#                  processing_time, ocr_engine, uploaded_by)
#                 VALUES (%s, %s, %s, %s, %s, %s, %s)
#                 RETURNING id
#             """
#             result = DatabaseOperations.execute_query(
#                 query,
#                 (filename, file_path, extracted_text, confidence_score,
#                  processing_time, ocr_engine, uploaded_by),
#                 fetch=True
#             )
#             return result[0]['id'] if result else None
#         except Exception as e:
#             print(f"Error saving document: {e}")
#             return None
    
#     @staticmethod
#     def get_dashboard_stats():
#         """Get dashboard statistics"""
#         stats = {
#             'total_invoices': 0,
#             'total_revenue': 0.0,
#             'paid_revenue': 0.0,
#             'pending_revenue': 0.0,
#             'recent_invoices': []
#         }
        
#         try:
#             # Total invoices
#             result = DatabaseOperations.execute_query(
#                 "SELECT COUNT(*) as count FROM ocr_documents"
#             )
#             stats['total_invoices'] = result[0]['count'] if result else 0
            
#             # Revenue stats
#             revenue_query = """
#                 SELECT 
#                     COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END), 0) as paid_amount,
#                     COALESCE(SUM(CASE WHEN payment_status IN ('unpaid', 'pending') THEN amount ELSE 0 END), 0) as pending_amount,
#                     COALESCE(SUM(amount), 0) as total_amount
#                 FROM ocr_documents
#                 WHERE amount IS NOT NULL
#             """
#             revenue = DatabaseOperations.execute_query(revenue_query)
#             if revenue:
#                 stats['paid_revenue'] = float(revenue[0]['paid_amount'] or 0)
#                 stats['pending_revenue'] = float(revenue[0]['pending_amount'] or 0)
#                 stats['total_revenue'] = float(revenue[0]['total_amount'] or 0)
            
#             # Recent transactions
#             recent_query = """
#                 SELECT 
#                     ocr.filename as bill_name,
#                     COALESCE(ocr.amount, 0) as amount,
#                     ocr.payment_status as status,
#                     COALESCE(dc.category, 'Uncategorized') as category,
#                     ocr.created_at as date
#                 FROM ocr_documents ocr
#                 LEFT JOIN document_categories dc ON ocr.id = dc.document_id
#                 ORDER BY ocr.created_at DESC
#                 LIMIT 10
#             """
#             stats['recent_invoices'] = DatabaseOperations.execute_query(recent_query) or []
            
#         except Exception as e:
#             print(f"Error fetching dashboard stats: {str(e)}")
        
#         return stats

"""
Database Operations - Full featured (audit logging enabled)

Features:
- psycopg2 + RealDictCursor connections with context manager
- parameterized queries with safe error handling
- save_ocr_document helper
- audit_log insertion helper
- dashboard & stats helpers
- initialize_database() with idempotent schema creation
- utility helpers for common DB operations

Notes:
- Uses DATABASE_URL when provided, otherwise individual env vars.
- In production you should replace prints with structured logging.
"""
import os
import json
from contextlib import contextmanager
from typing import Any, Optional, List, Dict, Tuple
from urllib.parse import urlparse
from datetime import datetime

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# ---------- Configuration helpers ----------
def _get_conn_params() -> Dict[str, Any]:
    """
    Resolve connection parameters from DATABASE_URL or individual env vars.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        try:
            url = urlparse(database_url)
            return {
                "host": url.hostname,
                "port": url.port or 5432,
                "database": url.path[1:],  # remove leading '/'
                "user": url.username,
                "password": url.password,
            }
        except Exception as e:
            print(f"[DB CONFIG] Failed to parse DATABASE_URL: {e}")
    # Fallback to components
    return {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", 5432)),
        "database": os.getenv("DB_NAME", "chatfinance_db"),
        "user": os.getenv("DB_USER", "postgres"),
        "password": os.getenv("DB_PASSWORD", ""),
    }

# ---------- Connection context manager ----------
@contextmanager
def get_db_connection():
    """
    Yields a psycopg2 connection with RealDictCursor.
    Commits on success, rollbacks on exception, always closes connection.
    """
    params = _get_conn_params()
    conn = None
    try:
        conn = psycopg2.connect(cursor_factory=RealDictCursor, **params)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

# ---------- DatabaseOperations class ----------
class DatabaseOperations:
    """
    Central DB helper used by API routes and core modules.
    Keep method signatures stable for backward compatibility.
    """

    @staticmethod
    def execute_query(query: str, params: Optional[Tuple] = None, fetch: bool = True) -> Any:
        """
        Execute a parameterized query.
        - query: SQL string with %s placeholders
        - params: tuple/list of parameters or None
        - fetch: if True return rows (list of dicts), else return rowcount (int)
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params or ())
                    if fetch:
                        rows = cur.fetchall()
                        return rows
                    return cur.rowcount
        except Exception as e:
            # In production replace with logger.exception(...)
            print(f"[DB ERROR] {e} -- Query: {query} -- Params: {params}")
            return [] if fetch else 0

    # ---------------------------
    # Specialized helpers
    # ---------------------------

    @staticmethod
    def save_ocr_document(filename: str,
                          file_path: str,
                          extracted_text: str,
                          confidence_score: float,
                          processing_time: float,
                          ocr_engine: str,
                          uploaded_by: Optional[int]) -> Optional[int]:
        """
        Insert an OCR document and return its id.
        Returns None on failure.
        """
        try:
            query = """
                INSERT INTO ocr_documents
                (filename, file_path, extracted_text, confidence_score, processing_time, ocr_engine, uploaded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            res = DatabaseOperations.execute_query(query, (filename, file_path, extracted_text,
                                                          confidence_score, processing_time, ocr_engine, uploaded_by), fetch=True)
            if res:
                return int(res[0]["id"])
            return None
        except Exception as e:
            print(f"[DB save_ocr_document] Error: {e}")
            return None

    @staticmethod
    def insert_document_category(document_id: int, category: str, confidence: float = 100.0, metadata: Optional[Dict] = None) -> bool:
        """
        Inserts a category record for a document. If metadata is provided, JSON-encode it.
        """
        try:
            meta_json = json.dumps(metadata) if metadata is not None else None
            query = """
                INSERT INTO document_categories (document_id, category, confidence, metadata)
                VALUES (%s, %s, %s, %s)
            """
            DatabaseOperations.execute_query(query, (document_id, category, confidence, meta_json), fetch=False)
            return True
        except Exception as e:
            print(f"[DB insert_document_category] Error: {e}")
            return False

    # ---------------------------
    # Audit logging
    # ---------------------------
    @staticmethod
    def audit_log(user_id: Optional[int], action: str, table_name: Optional[str] = None,
                  record_id: Optional[int] = None, old_values: Optional[Dict] = None, new_values: Optional[Dict] = None,
                  ip_address: Optional[str] = None) -> bool:
        """
        Insert an audit record for tracing changes.
        - old_values and new_values are stored as JSONB
        - This is best-effort: failure to write audit log should NOT block the main operation.
        """
        try:
            query = """
                INSERT INTO audit_log (user_id, action, table_name, record_id, old_values, new_values, ip_address, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            old_json = json.dumps(old_values) if old_values is not None else None
            new_json = json.dumps(new_values) if new_values is not None else None
            DatabaseOperations.execute_query(query, (user_id, action, table_name, record_id, old_json, new_json, ip_address), fetch=False)
            return True
        except Exception as e:
            # audit failures are non-fatal
            print(f"[AUDIT LOG ERROR] {e}")
            return False

    # ---------------------------
    # Dashboard & utility reports
    # ---------------------------
    @staticmethod
    def get_dashboard_stats(limit_recent: int = 10) -> Dict[str, Any]:
        """
        Returns summary stats used by the frontend dashboard:
        - total_invoices, total_revenue, paid_revenue, pending_revenue
        - recent_invoices (list)
        """
        stats: Dict[str, Any] = {
            "total_invoices": 0,
            "total_revenue": 0.0,
            "paid_revenue": 0.0,
            "pending_revenue": 0.0,
            "recent_invoices": []
        }
        try:
            # Total invoices
            res = DatabaseOperations.execute_query("SELECT COUNT(*) as count FROM ocr_documents", fetch=True)
            stats["total_invoices"] = int(res[0]["count"]) if res else 0

            # Revenue calculations
            revenue_query = """
                SELECT
                    COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN amount ELSE 0 END), 0) as paid_amount,
                    COALESCE(SUM(CASE WHEN payment_status IN ('unpaid', 'pending') THEN amount ELSE 0 END), 0) as pending_amount,
                    COALESCE(SUM(amount), 0) as total_amount
                FROM ocr_documents
                WHERE amount IS NOT NULL
            """
            rev = DatabaseOperations.execute_query(revenue_query, fetch=True)
            if rev:
                stats["paid_revenue"] = float(rev[0].get("paid_amount") or 0)
                stats["pending_revenue"] = float(rev[0].get("pending_amount") or 0)
                stats["total_revenue"] = float(rev[0].get("total_amount") or 0)

            # Recent transactions
            recent_q = """
                SELECT ocr.id, ocr.filename as bill_name, COALESCE(ocr.amount, 0) as amount,
                       ocr.payment_status as status, COALESCE(dc.category, 'Uncategorized') as category,
                       ocr.created_at as date
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                ORDER BY ocr.created_at DESC
                LIMIT %s
            """
            recent = DatabaseOperations.execute_query(recent_q, (limit_recent,), fetch=True) or []
            stats["recent_invoices"] = recent
        except Exception as e:
            print(f"[DB get_dashboard_stats] Error: {e}")
        return stats

    @staticmethod
    def get_category_stats(user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Returns simple category statistics (counts and sums). If user_id provided, filter by user.
        """
        try:
            params = []
            where = ""
            if user_id is not None:
                where = "WHERE ocr.uploaded_by = %s"
                params = [user_id]

            query = f"""
                SELECT dc.category, COUNT(*) as count, COALESCE(SUM(ocr.amount), 0) as total
                FROM ocr_documents ocr
                LEFT JOIN document_categories dc ON ocr.id = dc.document_id
                {where}
                GROUP BY dc.category
                ORDER BY total DESC
            """
            rows = DatabaseOperations.execute_query(query, tuple(params) if params else None, fetch=True) or []
            return {"categories": rows}
        except Exception as e:
            print(f"[DB get_category_stats] Error: {e}")
            return {"categories": []}

    # ---------------------------
    # Initialization
    # ---------------------------
    @staticmethod
    def initialize_database(schema_path: Optional[str] = None) -> bool:
        """
        Initialize DB schema. If a schema_path is given and exists, execute it; otherwise create minimal tables.
        Returns True on success.
        """
        try:
            # If a SQL schema file is present, execute it (useful for large schemas / migrations)
            if schema_path and os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    sql = f.read()
                with get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(sql)
                print("[DB INIT] Schema executed from file.")
                return True

            # Otherwise create minimal set of tables (idempotent)
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            id SERIAL PRIMARY KEY,
                            username VARCHAR(150) UNIQUE NOT NULL,
                            email VARCHAR(255) UNIQUE NOT NULL,
                            password_hash TEXT NOT NULL,
                            full_name VARCHAR(255),
                            role VARCHAR(50) DEFAULT 'user',
                            is_active BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            last_login TIMESTAMP
                        );
                        CREATE TABLE IF NOT EXISTS ocr_documents (
                            id SERIAL PRIMARY KEY,
                            filename VARCHAR(255) NOT NULL,
                            file_path TEXT,
                            extracted_text TEXT,
                            confidence_score DECIMAL(6,3),
                            processing_time DECIMAL(10,4),
                            ocr_engine VARCHAR(80),
                            uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                            payment_status VARCHAR(40) DEFAULT 'unpaid',
                            payment_date TIMESTAMP,
                            due_date DATE,
                            reminder_date DATE,
                            reminder_sent BOOLEAN DEFAULT FALSE,
                            amount DECIMAL(12,2),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE TABLE IF NOT EXISTS document_categories (
                            id SERIAL PRIMARY KEY,
                            document_id INTEGER REFERENCES ocr_documents(id) ON DELETE CASCADE,
                            category VARCHAR(200),
                            confidence DECIMAL(5,2),
                            metadata JSONB,
                            verified BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                        CREATE TABLE IF NOT EXISTS audit_log (
                            id SERIAL PRIMARY KEY,
                            user_id INTEGER,
                            action VARCHAR(150) NOT NULL,
                            table_name VARCHAR(100),
                            record_id INTEGER,
                            old_values JSONB,
                            new_values JSONB,
                            ip_address INET,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
            print("[DB INIT] Minimal schema ensured.")
            return True
        except Exception as e:
            print(f"[DB INIT ERROR] {e}")
            return False

# End of DatabaseOperations
