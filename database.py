import sqlite3
from contextlib import contextmanager
from pathlib import Path
import hashlib
from typing import Iterator, Optional, List, Dict, Any

DB_PATH = Path(__file__).resolve().parent / 'app.db'

@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db() -> None:
    with get_connection() as conn:
        c = conn.cursor()
        c.execute(
            '''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )'''
        )
        c.execute(
            '''CREATE TABLE IF NOT EXISTS memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                parent_id INTEGER NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_id) REFERENCES memos(id) ON DELETE SET NULL
            )'''
        )
        c.execute('CREATE INDEX IF NOT EXISTS idx_memos_user_id ON memos(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_memos_parent_id ON memos(parent_id)')
        c.execute(
            '''CREATE TABLE IF NOT EXISTS memo_sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memo_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                synced_at DATETIME NULL,
                local_updated_at DATETIME NOT NULL,
                status TEXT NOT NULL
            )'''
        )
        conn.commit()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email: str, password: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                'INSERT INTO users(email, password_hash) VALUES (?, ?)',
                (email, hash_password(password))
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(email: str, password: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(
            'SELECT * FROM users WHERE email = ? AND password_hash = ?',
            (email, hash_password(password))
        )
        return cur.fetchone()

def get_user(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cur.fetchone()

def list_memos(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(
            'SELECT * FROM memos WHERE user_id = ? ORDER BY created_at DESC',
            (user_id,)
        )
        return cur.fetchall()



def list_memos_all(user_id: int) -> list[sqlite3.Row]:
    """Return all memos for the user ordered by creation time."""
    with get_connection() as conn:
        cur = conn.execute(
            'SELECT * FROM memos WHERE user_id = ? ORDER BY created_at ASC',
            (user_id,),
        )
        return cur.fetchall()


def build_memo_tree(user_id: int) -> list[Dict[str, Any]]:
    """Return memos in a parent-child tree structure."""
    rows = list_memos_all(user_id)
    memos = [dict(r) for r in rows]
    lookup = {m['id']: m for m in memos}
    for m in memos:
        m['children'] = []
    roots: List[Dict[str, Any]] = []
    for m in memos:
        parent = lookup.get(m['parent_id'])
        if parent:
            parent['children'].append(m)
        else:
            roots.append(m)
    return roots

def create_memo(user_id: int, title: str, body: str, parent_id: int | None = None) -> int:
    with get_connection() as conn:
        conn.execute(
            'INSERT INTO memos(user_id, title, body, parent_id) VALUES (?, ?, ?, ?)',
            (user_id, title, body, parent_id)
        )
        conn.commit()
        return conn.execute('SELECT last_insert_rowid()').fetchone()[0]

def get_memo(memo_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute('SELECT * FROM memos WHERE id = ?', (memo_id,))
        return cur.fetchone()


def list_children(memo_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(
            'SELECT * FROM memos WHERE parent_id = ? ORDER BY created_at ASC',
            (memo_id,),
        )
        return cur.fetchall()

def update_memo(memo_id: int, title: str, body: str, parent_id: int | None) -> None:
    with get_connection() as conn:
        conn.execute(
            'UPDATE memos SET title = ?, body = ?, parent_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (title, body, parent_id, memo_id)
        )
        conn.commit()

def delete_memo(memo_id: int) -> None:
    with get_connection() as conn:
        conn.execute('DELETE FROM memos WHERE id = ?', (memo_id,))
        conn.commit()

def search_memos(user_id: int, keyword: str) -> list[sqlite3.Row]:
    kw = f'%{keyword}%'
    with get_connection() as conn:
        cur = conn.execute(
            'SELECT * FROM memos WHERE user_id = ? AND (title LIKE ? OR body LIKE ?) ORDER BY updated_at DESC',
            (user_id, kw, kw)
        )
        return cur.fetchall()
