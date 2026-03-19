from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from datetime import date, datetime
from uuid import UUID

from .builders import MealBuilder
from .events import DomainEventPublisher
from .models import Meal, MealItem, MealType
from .ports import MealRepository, ProductCatalog
from .products import (
    CachedProductCatalogProxy,
    NutritionCatalogAdapter,
    StaticNutritionProvider,
)


class SQLiteMealRepository(MealRepository):
    def __init__(self, conn: sqlite3.Connection, builder: MealBuilder) -> None:
        self._conn = conn
        self._builder = builder

    def add(self, meal: Meal) -> Meal:
        self._conn.execute(
            """
            INSERT INTO meals(id, user_id, meal_type, meal_date, original_text, total_calories, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(meal.id),
                str(meal.user_id),
                meal.meal_type.value,
                meal.meal_date.isoformat(),
                meal.original_text,
                meal.total_calories,
                meal.created_at.isoformat(),
                meal.updated_at.isoformat(),
            ),
        )
        self._persist_items(meal)
        return meal

    def update(self, meal: Meal) -> Meal:
        self._conn.execute(
            """
            UPDATE meals
            SET meal_type = ?, original_text = ?, total_calories = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                meal.meal_type.value,
                meal.original_text,
                meal.total_calories,
                meal.updated_at.isoformat(),
                str(meal.id),
            ),
        )
        self._conn.execute("DELETE FROM meal_items WHERE meal_id = ?", (str(meal.id),))
        self._persist_items(meal)
        return meal

    def delete(self, meal_id: UUID) -> bool:
        cursor = self._conn.execute("DELETE FROM meals WHERE id = ?", (str(meal_id),))
        return cursor.rowcount > 0

    def get(self, meal_id: UUID) -> Meal | None:
        meal_row = self._conn.execute(
            "SELECT * FROM meals WHERE id = ?",
            (str(meal_id),),
        ).fetchone()
        if not meal_row:
            return None
        return self._hydrate_meal(meal_row)

    def list_for_day(self, user_id: UUID, meal_date: date) -> list[Meal]:
        rows = self._conn.execute(
            """
            SELECT * FROM meals
            WHERE user_id = ? AND meal_date = ?
            ORDER BY created_at DESC
            """,
            (str(user_id), meal_date.isoformat()),
        ).fetchall()
        return [self._hydrate_meal(row) for row in rows]

    def day_summary(self, user_id: UUID, meal_date: date) -> tuple[int, int]:
        row = self._conn.execute(
            """
            SELECT COUNT(*) AS meals_count, COALESCE(SUM(total_calories), 0) AS total_calories
            FROM meals
            WHERE user_id = ? AND meal_date = ?
            """,
            (str(user_id), meal_date.isoformat()),
        ).fetchone()
        return row["meals_count"], row["total_calories"]

    def _hydrate_meal(self, meal_row: sqlite3.Row) -> Meal:
        builder = self._builder.from_persisted(
            meal_id=UUID(meal_row["id"]),
            user_id=UUID(meal_row["user_id"]),
            meal_type=MealType(meal_row["meal_type"]),
            meal_date=date.fromisoformat(meal_row["meal_date"]),
            original_text=meal_row["original_text"],
            created_at=datetime.fromisoformat(meal_row["created_at"]),
            updated_at=datetime.fromisoformat(meal_row["updated_at"]),
        )
        item_rows = self._conn.execute(
            """
            SELECT product_name, weight_grams, calories_per_100g, calories_total
            FROM meal_items
            WHERE meal_id = ?
            ORDER BY id
            """,
            (meal_row["id"],),
        ).fetchall()
        for row in item_rows:
            builder.add_prebuilt_item(
                MealItem(
                    product_name=row["product_name"],
                    weight_grams=row["weight_grams"],
                    calories_per_100g=row["calories_per_100g"],
                    calories_total=row["calories_total"],
                )
            )
        return builder.build()

    def _persist_items(self, meal: Meal) -> None:
        self._conn.executemany(
            """
            INSERT INTO meal_items(meal_id, product_name, weight_grams, calories_per_100g, calories_total)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    str(meal.id),
                    item.product_name,
                    item.weight_grams,
                    item.calories_per_100g,
                    item.calories_total,
                )
                for item in meal.items
            ],
        )


class LoggingMealRepository(MealRepository):
    def __init__(self, inner: MealRepository, publisher: DomainEventPublisher) -> None:
        self._inner = inner
        self._publisher = publisher

    def add(self, meal: Meal) -> Meal:
        saved = self._inner.add(meal)
        self._publisher.publish("meal.saved", {"meal_id": str(saved.id)})
        return saved

    def update(self, meal: Meal) -> Meal:
        updated = self._inner.update(meal)
        self._publisher.publish("meal.updated", {"meal_id": str(updated.id)})
        return updated

    def delete(self, meal_id: UUID) -> bool:
        deleted = self._inner.delete(meal_id)
        if deleted:
            self._publisher.publish("meal.deleted", {"meal_id": str(meal_id)})
        return deleted

    def get(self, meal_id: UUID) -> Meal | None:
        return self._inner.get(meal_id)

    def list_for_day(self, user_id: UUID, meal_date: date) -> list[Meal]:
        return self._inner.list_for_day(user_id, meal_date)

    def day_summary(self, user_id: UUID, meal_date: date) -> tuple[int, int]:
        return self._inner.day_summary(user_id, meal_date)


class AbstractServiceFactory(ABC):
    @abstractmethod
    def create_meal_repository(self) -> MealRepository:
        raise NotImplementedError

    @abstractmethod
    def create_product_catalog(self) -> ProductCatalog:
        raise NotImplementedError


class SQLiteServiceFactory(AbstractServiceFactory):
    def __init__(
        self,
        conn: sqlite3.Connection,
        builder: MealBuilder,
        publisher: DomainEventPublisher,
    ) -> None:
        self._conn = conn
        self._builder = builder
        self._publisher = publisher

    def create_meal_repository(self) -> MealRepository:
        repository = SQLiteMealRepository(self._conn, self._builder)
        return LoggingMealRepository(repository, self._publisher)

    def create_product_catalog(self) -> ProductCatalog:
        provider = StaticNutritionProvider(self._conn)
        adapter = NutritionCatalogAdapter(provider)
        return CachedProductCatalogProxy(adapter)
