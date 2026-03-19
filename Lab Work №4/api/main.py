from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, Response, status
from pydantic import BaseModel, Field

DB_PATH = Path(__file__).with_name("lab4.sqlite3")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _create_tables()
    _seed_data()
    yield


app = FastAPI(
    title="Calorie Voice Diary API",
    version="1.1.0",
    description="REST API для учета приемов пищи и расчета калорийности",
    lifespan=lifespan,
)


class MealType(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"


class MealItemIn(BaseModel):
    product_name: str = Field(min_length=1, max_length=100)
    weight_grams: int = Field(gt=0, le=2000)
    calories_per_100g: int = Field(gt=0, le=1000)


class MealCreateRequest(BaseModel):
    user_id: UUID
    meal_type: MealType
    meal_date: date
    original_text: str = Field(min_length=1, max_length=1000)
    items: List[MealItemIn] = Field(min_length=1)


class MealUpdateRequest(BaseModel):
    meal_type: MealType
    original_text: str = Field(min_length=1, max_length=1000)
    items: List[MealItemIn] = Field(min_length=1)


class VoiceProcessRequest(BaseModel):
    user_id: UUID
    text: str = Field(min_length=1, max_length=1000)
    meal_type: MealType
    meal_date: date


class MealItemOut(BaseModel):
    product_name: str
    weight_grams: int
    calories_per_100g: int
    calories_total: int


class MealResponse(BaseModel):
    id: UUID
    user_id: UUID
    meal_type: MealType
    meal_date: date
    original_text: str
    total_calories: int
    items: List[MealItemOut]
    created_at: datetime
    updated_at: datetime


class DaySummaryResponse(BaseModel):
    user_id: UUID
    meal_date: date
    meals_count: int
    total_calories: int


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _create_tables() -> None:
    with _get_conn() as conn:
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


def _seed_data() -> None:
    products = [
        ("apple", 52),
        ("chicken breast", 165),
        ("rice", 130),
        ("buckwheat", 343),
        ("banana", 89),
    ]

    with _get_conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO products(name, calories_per_100g) VALUES (?, ?)",
            products,
        )

        meals_count = conn.execute("SELECT COUNT(*) AS c FROM meals").fetchone()["c"]
        if meals_count > 0:
            return

        now = _utc_now_iso()
        seed_meal_id = str(uuid4())
        seed_user_id = "77f496bb-9f04-48be-a03d-cb3ccf6c10a5"
        conn.execute(
            """
            INSERT INTO meals(id, user_id, meal_type, meal_date, original_text, total_calories, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seed_meal_id,
                seed_user_id,
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
            (seed_meal_id, "banana", 120, 89, 107),
        )


def _calc_item(item: MealItemIn) -> MealItemOut:
    calories_total = round(item.weight_grams * item.calories_per_100g / 100)
    return MealItemOut(
        product_name=item.product_name,
        weight_grams=item.weight_grams,
        calories_per_100g=item.calories_per_100g,
        calories_total=calories_total,
    )


def _build_meal_response(
    meal_row: sqlite3.Row, conn: sqlite3.Connection
) -> MealResponse:
    item_rows = conn.execute(
        """
        SELECT product_name, weight_grams, calories_per_100g, calories_total
        FROM meal_items
        WHERE meal_id = ?
        ORDER BY id
        """,
        (meal_row["id"],),
    ).fetchall()

    items = [
        MealItemOut(
            product_name=row["product_name"],
            weight_grams=row["weight_grams"],
            calories_per_100g=row["calories_per_100g"],
            calories_total=row["calories_total"],
        )
        for row in item_rows
    ]

    return MealResponse(
        id=UUID(meal_row["id"]),
        user_id=UUID(meal_row["user_id"]),
        meal_type=MealType(meal_row["meal_type"]),
        meal_date=date.fromisoformat(meal_row["meal_date"]),
        original_text=meal_row["original_text"],
        total_calories=meal_row["total_calories"],
        items=items,
        created_at=datetime.fromisoformat(meal_row["created_at"]),
        updated_at=datetime.fromisoformat(meal_row["updated_at"]),
    )


def _create_meal(payload: MealCreateRequest) -> MealResponse:
    now = _utc_now_iso()
    meal_id = str(uuid4())
    items = [_calc_item(i) for i in payload.items]
    total = sum(i.calories_total for i in items)

    with _get_conn() as conn:
        conn.execute(
            """
            INSERT INTO meals(id, user_id, meal_type, meal_date, original_text, total_calories, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meal_id,
                str(payload.user_id),
                payload.meal_type.value,
                payload.meal_date.isoformat(),
                payload.original_text,
                total,
                now,
                now,
            ),
        )

        conn.executemany(
            """
            INSERT INTO meal_items(meal_id, product_name, weight_grams, calories_per_100g, calories_total)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    meal_id,
                    item.product_name,
                    item.weight_grams,
                    item.calories_per_100g,
                    item.calories_total,
                )
                for item in items
            ],
        )

        meal_row = conn.execute(
            "SELECT * FROM meals WHERE id = ?", (meal_id,)
        ).fetchone()
        return _build_meal_response(meal_row, conn)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/products")
def list_products(
    q: str | None = Query(default=None, max_length=100),
) -> Dict[str, List[Dict[str, int | str]]]:
    with _get_conn() as conn:
        if q:
            rows = conn.execute(
                """
                SELECT name, calories_per_100g
                FROM products
                WHERE LOWER(name) LIKE LOWER(?)
                ORDER BY name
                """,
                (f"%{q}%",),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT name, calories_per_100g FROM products ORDER BY name"
            ).fetchall()

    return {
        "products": [
            {"product_name": row["name"], "calories_per_100g": row["calories_per_100g"]}
            for row in rows
        ]
    }


@app.get("/api/v1/meals", response_model=List[MealResponse])
def list_meals(
    user_id: UUID,
    meal_date: date,
) -> List[MealResponse]:
    with _get_conn() as conn:
        rows = conn.execute(
            """
            SELECT * FROM meals
            WHERE user_id = ? AND meal_date = ?
            ORDER BY created_at DESC
            """,
            (str(user_id), meal_date.isoformat()),
        ).fetchall()
        return [_build_meal_response(row, conn) for row in rows]


@app.get("/api/v1/meals/{meal_id}", response_model=MealResponse)
def get_meal(meal_id: UUID) -> MealResponse:
    with _get_conn() as conn:
        meal_row = conn.execute(
            "SELECT * FROM meals WHERE id = ?", (str(meal_id),)
        ).fetchone()
        if not meal_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found"
            )
        return _build_meal_response(meal_row, conn)


@app.get("/api/v1/reports/day-summary", response_model=DaySummaryResponse)
def day_summary(user_id: UUID, meal_date: date) -> DaySummaryResponse:
    with _get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS meals_count, COALESCE(SUM(total_calories), 0) AS total_calories
            FROM meals
            WHERE user_id = ? AND meal_date = ?
            """,
            (str(user_id), meal_date.isoformat()),
        ).fetchone()

    return DaySummaryResponse(
        user_id=user_id,
        meal_date=meal_date,
        meals_count=row["meals_count"],
        total_calories=row["total_calories"],
    )


@app.post(
    "/api/v1/meals", response_model=MealResponse, status_code=status.HTTP_201_CREATED
)
def create_meal(payload: MealCreateRequest) -> MealResponse:
    return _create_meal(payload)


@app.post(
    "/api/v1/voice/process",
    response_model=MealResponse,
    status_code=status.HTTP_201_CREATED,
)
def process_voice(payload: VoiceProcessRequest) -> MealResponse:
    text = payload.text.lower()

    parsed_items = []
    if "chicken" in text:
        parsed_items.append(
            MealItemIn(
                product_name="chicken breast", weight_grams=200, calories_per_100g=165
            )
        )
    if "apple" in text:
        parsed_items.append(
            MealItemIn(product_name="apple", weight_grams=150, calories_per_100g=52)
        )

    if not parsed_items:
        parsed_items.append(
            MealItemIn(product_name="banana", weight_grams=120, calories_per_100g=89)
        )

    create_request = MealCreateRequest(
        user_id=payload.user_id,
        meal_type=payload.meal_type,
        meal_date=payload.meal_date,
        original_text=payload.text,
        items=parsed_items,
    )
    return _create_meal(create_request)


@app.put("/api/v1/meals/{meal_id}", response_model=MealResponse)
def update_meal(meal_id: UUID, payload: MealUpdateRequest) -> MealResponse:
    with _get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM meals WHERE id = ?", (str(meal_id),)
        ).fetchone()
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found"
            )

        items = [_calc_item(i) for i in payload.items]
        total = sum(i.calories_total for i in items)

        conn.execute(
            """
            UPDATE meals
            SET meal_type = ?, original_text = ?, total_calories = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.meal_type.value,
                payload.original_text,
                total,
                _utc_now_iso(),
                str(meal_id),
            ),
        )

        conn.execute("DELETE FROM meal_items WHERE meal_id = ?", (str(meal_id),))
        conn.executemany(
            """
            INSERT INTO meal_items(meal_id, product_name, weight_grams, calories_per_100g, calories_total)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    str(meal_id),
                    item.product_name,
                    item.weight_grams,
                    item.calories_per_100g,
                    item.calories_total,
                )
                for item in items
            ],
        )

        meal_row = conn.execute(
            "SELECT * FROM meals WHERE id = ?", (str(meal_id),)
        ).fetchone()
        return _build_meal_response(meal_row, conn)


@app.delete("/api/v1/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(meal_id: UUID) -> Response:
    with _get_conn() as conn:
        deleted = conn.execute(
            "DELETE FROM meals WHERE id = ?", (str(meal_id),)
        ).rowcount
        if deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found"
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
