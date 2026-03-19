from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from .settings import Settings, SingletonMeta


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Database(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._db_path = Settings().db_path

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    name TEXT PRIMARY KEY,
                    calories_per_100g INTEGER NOT NULL CHECK(calories_per_100g > 0)
                );

                CREATE TABLE IF NOT EXISTS meals (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    meal_type TEXT NOT NULL,
                    meal_date TEXT NOT NULL,
                    original_text TEXT NOT NULL,
                    total_calories INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS meal_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meal_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    weight_grams INTEGER NOT NULL,
                    calories_per_100g INTEGER NOT NULL,
                    calories_total INTEGER NOT NULL,
                    FOREIGN KEY(meal_id) REFERENCES meals(id) ON DELETE CASCADE
                );
                """
            )

            conn.executemany(
                "INSERT OR IGNORE INTO products(name, calories_per_100g) VALUES (?, ?)",
                [
                    ("apple", 52),
                    ("chicken breast", 165),
                    ("rice", 130),
                    ("buckwheat", 343),
                    ("banana", 89),
                ],
            )

            meals_count = conn.execute("SELECT COUNT(*) AS c FROM meals").fetchone()[
                "c"
            ]
            if meals_count:
                return

            now = utc_now().isoformat()
            meal_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO meals(id, user_id, meal_type, meal_date, original_text, total_calories, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    meal_id,
                    "77f496bb-9f04-48be-a03d-cb3ccf6c10a5",
                    "breakfast",
                    "2026-02-18",
                    "Seed meal: banana",
                    107,
                    now,
                    now,
                ),
            )
            conn.execute(
                """
                INSERT INTO meal_items(meal_id, product_name, weight_grams, calories_per_100g, calories_total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (meal_id, "banana", 120, 89, 107),
            )
