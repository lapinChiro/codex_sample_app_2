import sqlite3
from contextlib import closing
from passlib.hash import bcrypt

DB_PATH = 'memo.db'

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS memos (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            title TEXT NOT NULL,
            content TEXT,
            parent_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(parent_id) REFERENCES memos(id) ON DELETE SET NULL
        );
        """)
        conn.commit()


def create_user(email: str, password: str):
    password_hash = bcrypt.hash(password)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        try:
            conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False


def authenticate(email: str, password: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        if row and bcrypt.verify(password, row[1]):
            return row[0]
        return None


def create_memo(user_id: int, title: str, content: str = '', parent_id: str | None = None, memo_id: str | None = None):
    import uuid
    if memo_id is None:
        memo_id = str(uuid.uuid4())
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO memos (id, user_id, title, content, parent_id) VALUES (?,?,?,?,?)",
            (memo_id, user_id, title, content, parent_id)
        )
        conn.commit()
        return memo_id


def update_memo(memo_id: str, title: str, content: str, parent_id: str | None):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "UPDATE memos SET title=?, content=?, parent_id=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (title, content, parent_id, memo_id)
        )
        conn.commit()


def delete_memo(memo_id: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("DELETE FROM memos WHERE id=?", (memo_id,))
        conn.commit()


def get_memo(memo_id: str):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT id, title, content, parent_id FROM memos WHERE id=?",
            (memo_id,)
        ).fetchone()
        return row


def list_memos(user_id: int):
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT id, title, parent_id FROM memos WHERE user_id=? ORDER BY created_at",
            (user_id,)
        ).fetchall()
        return rows


def search_memos(user_id: int, query: str):
    q = f"%{query}%"
    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT id, title FROM memos WHERE user_id=? AND (title LIKE ? OR content LIKE ?)",
            (user_id, q, q)
        ).fetchall()
        return rows


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """Update user's password after verifying the old password."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        if not row or not bcrypt.verify(old_password, row[0]):
            return False
        new_hash = bcrypt.hash(new_password)
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (new_hash, user_id),
        )
        conn.commit()
        return True

