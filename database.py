import json
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt

# ADJUST for local Postgres
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "whatsapp_analyzer"
DB_USER = "kndn12"   # <- change to your PG user
DB_PASSWORD = None   # None for peer-auth local

def _conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD, cursor_factory=RealDictCursor
    )

def init_schema():
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password BYTEA,
            name VARCHAR(255) NOT NULL,
            google_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            kpi_json JSONB NOT NULL,
            summary_text TEXT,
            pdf_path TEXT,
            docx_path TEXT
        );
        """)

def create_report(user_email: str, title: str, kpis: dict, summary_text: str | None = None) -> int:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO reports (user_email,title,kpi_json,summary_text) VALUES (%s,%s,%s,%s) RETURNING id",
            (user_email, title, json.dumps(kpis), summary_text),
        )
        return cur.fetchone()["id"]

def list_reports(user_email: str):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id,title,created_at FROM reports WHERE user_email=%s ORDER BY created_at DESC",
            (user_email,),
        )
        return cur.fetchall()

def get_report(report_id: int):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM reports WHERE id=%s", (report_id,))
        row = cur.fetchone()
        if not row:
            return None
        # Ensure kpi_json is a dict
        kpi = row.get("kpi_json")
        if isinstance(kpi, str):
            try:
                row["kpi_json"] = json.loads(kpi)
            except Exception:
                pass
        return row

def user_exists(email: str) -> bool:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE email=%s", (email,))
        return cur.fetchone() is not None

def get_user(email: str):
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT email,name,created_at FROM users WHERE email=%s", (email,))
        return cur.fetchone()

def update_user_name(email: str, new_name: str) -> bool:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET name=%s WHERE email=%s", (new_name, email))
        return cur.rowcount > 0

def change_user_password(email: str, new_password: str) -> bool:
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE users SET hashed_password=%s WHERE email=%s", (psycopg2.Binary(hashed), email))
        return cur.rowcount > 0

def delete_report(report_id: int, user_email: str) -> bool:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM reports WHERE id=%s AND user_email=%s", (report_id, user_email))
        return cur.rowcount > 0

def count_reports(email: str) -> int:
    with _conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM reports WHERE user_email=%s", (email,))
        row = cur.fetchone()
        return int(row["c"]) if row else 0
