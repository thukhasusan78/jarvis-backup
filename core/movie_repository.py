"""Movie SQLite repository — anti-dupe and series index storage."""
import sqlite3
from typing import Optional, Dict, Any

from core.db import connect_db

DB_FILE = "movies_memory.db"


def init_db():
    conn = connect_db(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS downloaded_movies (
            tmdb_id INTEGER PRIMARY KEY,
            title TEXT,
            media_type TEXT,
            target_channel TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)'''
    )
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS series_index (
            series_key TEXT PRIMARY KEY,
            message_id INTEGER,
            buttons_data TEXT,
            series_data TEXT)'''
    )
    conn.commit()
    conn.close()


def get_series_index(series_key: str) -> Optional[Dict[str, Any]]:
    conn = connect_db(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS series_index (
            series_key TEXT PRIMARY KEY, message_id INTEGER, buttons_data TEXT, series_data TEXT)'''
    )
    try:
        cursor.execute(
            "SELECT message_id, buttons_data, series_data FROM series_index WHERE series_key = ?",
            (series_key,),
        )
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE series_index ADD COLUMN series_data TEXT")
        cursor.execute(
            "SELECT message_id, buttons_data, series_data FROM series_index WHERE series_key = ?",
            (series_key,),
        )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "message_id": result[0],
            "buttons_data": result[1],
            "series_data": result[2] if len(result) > 2 else None,
        }
    return None


def save_series_index(series_key: str, message_id: int, buttons_data: str, series_data: str = None):
    conn = connect_db(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS series_index (
            series_key TEXT PRIMARY KEY, message_id INTEGER, buttons_data TEXT, series_data TEXT)'''
    )
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO series_index (series_key, message_id, buttons_data, series_data) VALUES (?, ?, ?, ?)",
            (series_key, message_id, buttons_data, series_data),
        )
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE series_index ADD COLUMN series_data TEXT")
        cursor.execute(
            "INSERT OR REPLACE INTO series_index (series_key, message_id, buttons_data, series_data) VALUES (?, ?, ?, ?)",
            (series_key, message_id, buttons_data, series_data),
        )
    conn.commit()
    conn.close()


def is_movie_downloaded(tmdb_id: int) -> bool:
    conn = connect_db(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM downloaded_movies WHERE tmdb_id = ?", (tmdb_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result)


def is_movie_title_downloaded(title: str) -> bool:
    conn = connect_db(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM downloaded_movies WHERE title LIKE ?", (title.strip(),))
    result = cursor.fetchone()
    conn.close()
    return bool(result)


def mark_movie_downloaded(tmdb_id: int, title: str, media_type: str, target_channel: str):
    conn = connect_db(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS downloaded_movies (
            tmdb_id INTEGER PRIMARY KEY,
            title TEXT,
            media_type TEXT,
            target_channel TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)'''
    )
    cursor.execute(
        "INSERT OR IGNORE INTO downloaded_movies (tmdb_id, title, media_type, target_channel) VALUES (?, ?, ?, ?)",
        (tmdb_id, title, media_type, target_channel),
    )
    conn.commit()
    conn.close()
