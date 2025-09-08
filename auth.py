import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from google_auth_oauthlib.flow import Flow

DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "whatsapp_analyzer"
DB_USER = "kndn12"
DB_PASSWORD = None

def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor
    )
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password BYTEA,
                name VARCHAR(255) NOT NULL,
                google_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            ''')
    conn.close()

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)

GOOGLE_CLIENT_ID = "465308747453-2n7fo3tunri5u01i9s7crl8smsc9sar6.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:8501"
SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email"
]

def create_flow():
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    return flow

def register_user(email: str, password: str, name: str):
    conn = get_db_connection()
    hashed = hash_password(password)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute('INSERT INTO users (email, hashed_password, name) VALUES (%s, %s, %s)', (email, hashed, name))
        return True
    except psycopg2.errors.UniqueViolation:
        return False
    finally:
        conn.close()

def login_user(email: str, password: str):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT hashed_password FROM users WHERE email = %s', (email,))
            user = cur.fetchone()
            if user:
                # Convert memoryview to bytes
                hashed_password_bytes = bytes(user['hashed_password'])
                if check_password(password, hashed_password_bytes):
                    return True
        return False
    finally:
        conn.close()
