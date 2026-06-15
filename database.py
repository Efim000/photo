import sqlite3
import hashlib
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any

class Database:
    def __init__(self, db_path: str = "photo_collection.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Создаёт и возвращает соединение с БД."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Создаёт таблицы users и photos, если они не существуют."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    date_taken TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    category TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
                )
            """)
            admin_password = hashlib.sha256("admin123".encode()).hexdigest()
            cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    ("admin", admin_password, "admin")
                )
            conn.commit()

    def register_user(self, username: str, password: str) -> bool:
        """Регистрирует нового пользователя с ролью 'user'. Возвращает True при успехе."""
        hashed = hashlib.sha256(password.encode()).hexdigest()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, hashed, "user")
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Проверяет учётные данные. Возвращает словарь с информацией о пользователе или None."""
        hashed = hashlib.sha256(password.encode()).hexdigest()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, username, role FROM users WHERE username = ? AND password = ?",
                (username, hashed)
            )
            row = cursor.fetchone()
            if row:
                return {"id": row["id"], "username": row["username"], "role": row["role"]}
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает информацию о пользователе по ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                return {"id": row["id"], "username": row["username"], "role": row["role"]}
            return None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Возвращает список всех пользователей (id, username, role)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role FROM users ORDER BY username")
            return [{"id": row["id"], "username": row["username"], "role": row["role"]} for row in cursor.fetchall()]

    def delete_user(self, user_id: int) -> None:
        """Удаляет пользователя и все его фотографии (каскадное удаление)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()

    def reset_password(self, user_id: int, new_password: str) -> None:
        """Сбрасывает пароль пользователя."""
        hashed = hashlib.sha256(new_password.encode()).hexdigest()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password = ? WHERE id = ?", (hashed, user_id))
            conn.commit()

    def add_photo(self, user_id: int, title: str, description: str,
                  date_taken: str, file_path: str, tags: str, category: str) -> None:
        """Добавляет новую фотографию в БД."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO photos (user_id, title, description, date_taken, file_path, tags, category)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, title, description, date_taken, file_path, tags, category))
            conn.commit()

    def delete_photo(self, photo_id: int, user_id: int) -> bool:
        """Удаляет фотографию, принадлежащую данному пользователю. Возвращает True, если удалено."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM photos WHERE id = ? AND user_id = ?", (photo_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

    def get_photos(self, user_id: int, tag_filter: Optional[str] = None,
                   start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Возвращает список фотографий пользователя с возможной фильтрацией по тегу и диапазону дат.
        tag_filter: искать точное совпадение тега (без учёта регистра, разделитель запятая)
        start_date, end_date: строки формата YYYY-MM-DD
        """
        query = "SELECT * FROM photos WHERE user_id = ?"
        params = [user_id]

        if tag_filter:
            query += " AND (',' || tags || ',') LIKE ?"
            params.append(f"%,{tag_filter.strip()},%")

        if start_date:
            query += " AND date_taken >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date_taken <= ?"
            params.append(end_date)

        query += " ORDER BY date_taken DESC, title"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_all_unique_tags(self, user_id: int) -> List[str]:
        """Возвращает список уникальных тегов, используемых пользователем."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT tags FROM photos WHERE user_id = ?", (user_id,))
            rows = cursor.fetchall()
            tags_set = set()
            for row in rows:
                if row["tags"]:
                    for tag in row["tags"].split(','):
                        cleaned = tag.strip()
                        if cleaned:
                            tags_set.add(cleaned)
            return sorted(tags_set)

    def get_photo_by_id(self, photo_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Возвращает фотографию по ID, если она принадлежит пользователю."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM photos WHERE id = ? AND user_id = ?", (photo_id, user_id))
            row = cursor.fetchone()
            return dict(row) if row else None