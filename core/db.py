import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_DIR = os.path.join(os.path.expanduser("~"), ".github_repo_manager")
DB_FILE = os.path.join(DB_DIR, "data.sqlite3")

def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Profiles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            token TEXT NOT NULL,
            username TEXT,
            avatar_url TEXT,
            bio TEXT,
            is_active INTEGER DEFAULT 0,
            created_at TEXT,
            last_used TEXT
        )
    """)

    # Cached repositories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cached_repos (
            id INTEGER PRIMARY KEY,
            profile_id INTEGER,
            full_name TEXT NOT NULL,
            name TEXT NOT NULL,
            owner TEXT NOT NULL,
            description TEXT,
            is_private INTEGER DEFAULT 0,
            is_fork INTEGER DEFAULT 0,
            stars INTEGER DEFAULT 0,
            forks INTEGER DEFAULT 0,
            open_issues INTEGER DEFAULT 0,
            default_branch TEXT DEFAULT 'main',
            language TEXT,
            html_url TEXT,
            clone_url TEXT,
            ssh_url TEXT,
            size INTEGER DEFAULT 0,
            pushed_at TEXT,
            updated_at TEXT,
            cached_at TEXT,
            UNIQUE(profile_id, full_name)
        )
    """)

    # Local projects table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS local_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            path TEXT UNIQUE NOT NULL,
            remote_url TEXT,
            repo_full_name TEXT,
            current_branch TEXT,
            last_opened TEXT,
            is_favorite INTEGER DEFAULT 0
        )
    """)

    # App Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Activity logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            level TEXT,
            action TEXT,
            details TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_connection():
    init_db()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


# --- Profile Management ---
def get_profiles() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles ORDER BY is_active DESC, id DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_active_profile() -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM profiles WHERE is_active = 1 LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_profile(name: str, token: str, username: str = "", avatar_url: str = "", bio: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    
    # Check if any profile is active; if none, make this active
    cursor.execute("SELECT COUNT(*) FROM profiles WHERE is_active = 1")
    has_active = cursor.fetchone()[0] > 0
    is_active = 1 if not has_active else 0

    cursor.execute("""
        INSERT INTO profiles (name, token, username, avatar_url, bio, is_active, created_at, last_used)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, token, username, avatar_url, bio, is_active, now, now))
    
    profile_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return profile_id


def update_profile_info(profile_id: int, username: str, avatar_url: str, bio: str):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        UPDATE profiles SET username = ?, avatar_url = ?, bio = ?, last_used = ?
        WHERE id = ?
    """, (username, avatar_url, bio, now, profile_id))
    conn.commit()
    conn.close()


def set_active_profile(profile_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE profiles SET is_active = 0")
    cursor.execute("UPDATE profiles SET is_active = 1, last_used = ? WHERE id = ?", 
                   (datetime.now().isoformat(), profile_id))
    conn.commit()
    conn.close()


def delete_profile(profile_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
    cursor.execute("DELETE FROM cached_repos WHERE profile_id = ?", (profile_id,))
    
    # If the active one was deleted, make another profile active if available
    cursor.execute("SELECT id FROM profiles LIMIT 1")
    first = cursor.fetchone()
    if first:
        cursor.execute("UPDATE profiles SET is_active = 1 WHERE id = ?", (first[0],))
        
    conn.commit()
    conn.close()


# --- Cached Repositories ---
def save_cached_repos(profile_id: int, repos: List[Dict[str, Any]]):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    cursor.execute("DELETE FROM cached_repos WHERE profile_id = ?", (profile_id,))

    for r in repos:
        cursor.execute("""
            INSERT OR REPLACE INTO cached_repos (
                profile_id, full_name, name, owner, description,
                is_private, is_fork, stars, forks, open_issues,
                default_branch, language, html_url, clone_url, ssh_url,
                size, pushed_at, updated_at, cached_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id, r.get('full_name', ''), r.get('name', ''), r.get('owner', ''),
            r.get('description', ''), 1 if r.get('is_private') else 0,
            1 if r.get('is_fork') else 0, r.get('stars', 0), r.get('forks', 0),
            r.get('open_issues', 0), r.get('default_branch', 'main'),
            r.get('language', ''), r.get('html_url', ''), r.get('clone_url', ''),
            r.get('ssh_url', ''), r.get('size', 0), r.get('pushed_at', ''),
            r.get('updated_at', ''), now
        ))

    conn.commit()
    conn.close()


def get_cached_repos(profile_id: int) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cached_repos WHERE profile_id = ? ORDER BY updated_at DESC", (profile_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# --- Local Projects ---
def add_or_update_local_project(name: str, path: str, remote_url: str = "", 
                                repo_full_name: str = "", current_branch: str = "main"):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO local_projects (name, path, remote_url, repo_full_name, current_branch, last_opened)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(path) DO UPDATE SET
            name = excluded.name,
            remote_url = excluded.remote_url,
            repo_full_name = excluded.repo_full_name,
            current_branch = excluded.current_branch,
            last_opened = excluded.last_opened
    """, (name, path, remote_url, repo_full_name, current_branch, now))
    conn.commit()
    conn.close()


def get_local_projects() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM local_projects ORDER BY last_opened DESC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def remove_local_project(project_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM local_projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


# --- App Settings ---
def get_setting(key: str, default: Any = None) -> Any:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return default
    try:
        return json.loads(row[0])
    except Exception:
        return row[0]


def set_setting(key: str, value: Any):
    conn = get_connection()
    cursor = conn.cursor()
    serialized = json.dumps(value) if not isinstance(value, str) else value
    cursor.execute("""
        INSERT INTO app_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, serialized))
    conn.commit()
    conn.close()


# --- Activity Logging ---
def log_activity(action: str, details: str = "", level: str = "INFO"):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO activity_logs (timestamp, level, action, details)
        VALUES (?, ?, ?, ?)
    """, (now, level, action, details))
    conn.commit()
    conn.close()


def get_recent_activity(limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM activity_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
