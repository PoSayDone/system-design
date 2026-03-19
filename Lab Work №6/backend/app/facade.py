from __future__ import annotations

import sqlite3
from datetime import date
from uuid import UUID

from .builders import MealBuilder
from .commands import (
    CreateMealCommand,
    CreateMealHandler,
    DeleteMealCommand,
    DeleteMealHandler,
    ProcessVoiceCommand,
    ProcessVoiceHandler,
    UpdateMealCommand,
    UpdateMealHandler,
)
from .database import Database
from .events import AuditLogSubscriber, DomainEventPublisher
from .models import (
    DaySummaryResponse,
    MealCreateRequest,
    MealResponse,
    MealUpdateRequest,
    VoiceProcessRequest,
)
from .repositories import SQLiteServiceFactory
from .voice import build_voice_chain


class CalorieDiaryFacade:
    def __init__(self, database: Database | None = None) -> None:
        self._database = database or Database()
        self._publisher = DomainEventPublisher()
        self.audit_log = AuditLogSubscriber()
        self._publisher.subscribe(self.audit_log)

        def factory_builder(conn: sqlite3.Connection):
            return SQLiteServiceFactory(conn, MealBuilder(), self._publisher)

        self._create_handler = CreateMealHandler(
            self._database, factory_builder, MealBuilder()
        )
        self._update_handler = UpdateMealHandler(
            self._database, factory_builder, MealBuilder()
        )
        self._delete_handler = DeleteMealHandler(self._database, factory_builder)
        self._voice_handler = ProcessVoiceHandler(
            self._database,
            factory_builder,
            build_voice_chain(),
            MealBuilder(),
        )
        self._factory_builder = factory_builder

    def list_products(
        self, query: str | None = None
    ) -> dict[str, list[dict[str, int | str]]]:
        with self._database.connection() as conn:
            catalog = self._factory_builder(conn).create_product_catalog()
            return {
                "products": [
                    {
                        "product_name": product.product_name,
                        "calories_per_100g": product.calories_per_100g,
                    }
                    for product in catalog.list_products(query)
                ]
            }

    def list_meals(self, user_id: UUID, meal_date: date) -> list[MealResponse]:
        with self._database.connection() as conn:
            repository = self._factory_builder(conn).create_meal_repository()
            return [
                meal.to_response()
                for meal in repository.list_for_day(user_id, meal_date)
            ]

    def get_meal(self, meal_id: UUID) -> MealResponse | None:
        with self._database.connection() as conn:
            repository = self._factory_builder(conn).create_meal_repository()
            meal = repository.get(meal_id)
            return meal.to_response() if meal else None

    def day_summary(self, user_id: UUID, meal_date: date) -> DaySummaryResponse:
        with self._database.connection() as conn:
            repository = self._factory_builder(conn).create_meal_repository()
            meals_count, total_calories = repository.day_summary(user_id, meal_date)
            return DaySummaryResponse(
                user_id=user_id,
                meal_date=meal_date,
                meals_count=meals_count,
                total_calories=total_calories,
            )

    def create_meal(self, payload: MealCreateRequest) -> MealResponse:
        return self._create_handler.handle(CreateMealCommand(payload))

    def update_meal(self, meal_id: UUID, payload: MealUpdateRequest) -> MealResponse:
        return self._update_handler.handle(
            UpdateMealCommand(
                meal_id=meal_id,
                meal_type=payload.meal_type,
                original_text=payload.original_text,
                items=payload.items,
            )
        )

    def delete_meal(self, meal_id: UUID) -> None:
        self._delete_handler.handle(DeleteMealCommand(meal_id))

    def process_voice(self, payload: VoiceProcessRequest) -> MealResponse:
        return self._voice_handler.handle(ProcessVoiceCommand(payload))
