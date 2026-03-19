from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import HTTPException, status

from .builders import MealBuilder
from .database import Database, utc_now
from .models import MealCreateRequest, MealResponse, MealType, VoiceProcessRequest
from .repositories import AbstractServiceFactory
from .voice import KeywordVoiceParser


@dataclass(slots=True)
class CreateMealCommand:
    payload: MealCreateRequest


@dataclass(slots=True)
class UpdateMealCommand:
    meal_id: UUID
    meal_type: MealType
    original_text: str
    items: list


@dataclass(slots=True)
class DeleteMealCommand:
    meal_id: UUID


@dataclass(slots=True)
class ProcessVoiceCommand:
    payload: VoiceProcessRequest


class BaseCommandHandler(ABC):
    def __init__(self, database: Database, factory_builder) -> None:
        self._database = database
        self._factory_builder = factory_builder

    def handle(self, command):
        with self._database.connection() as conn:
            factory = self._factory_builder(conn)
            return self.execute(command, factory)

    @abstractmethod
    def execute(self, command, factory: AbstractServiceFactory):
        raise NotImplementedError


class CreateMealHandler(BaseCommandHandler):
    def __init__(
        self, database: Database, factory_builder, builder: MealBuilder
    ) -> None:
        super().__init__(database, factory_builder)
        self._builder = builder

    def execute(
        self,
        command: CreateMealCommand,
        factory: AbstractServiceFactory,
    ) -> MealResponse:
        meal = self._builder.from_request(command.payload).build()
        saved = factory.create_meal_repository().add(meal)
        return saved.to_response()


class UpdateMealHandler(BaseCommandHandler):
    def __init__(
        self, database: Database, factory_builder, builder: MealBuilder
    ) -> None:
        super().__init__(database, factory_builder)
        self._builder = builder

    def execute(
        self,
        command: UpdateMealCommand,
        factory: AbstractServiceFactory,
    ) -> MealResponse:
        repository = factory.create_meal_repository()
        existing = repository.get(command.meal_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal not found",
            )

        payload = MealCreateRequest(
            user_id=existing.user_id,
            meal_type=command.meal_type,
            meal_date=existing.meal_date,
            original_text=command.original_text,
            items=command.items,
        )
        meal = (
            self._builder.from_request(payload)
            .change_identity(command.meal_id)
            .touch(utc_now())
            .build()
        )
        meal.created_at = existing.created_at
        updated = repository.update(meal)
        return updated.to_response()


class DeleteMealHandler(BaseCommandHandler):
    def execute(
        self, command: DeleteMealCommand, factory: AbstractServiceFactory
    ) -> None:
        deleted = factory.create_meal_repository().delete(command.meal_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meal not found",
            )


class ProcessVoiceHandler(BaseCommandHandler):
    def __init__(
        self,
        database: Database,
        factory_builder,
        voice_parser: KeywordVoiceParser,
        builder: MealBuilder,
    ) -> None:
        super().__init__(database, factory_builder)
        self._voice_parser = voice_parser
        self._builder = builder

    def execute(
        self,
        command: ProcessVoiceCommand,
        factory: AbstractServiceFactory,
    ) -> MealResponse:
        catalog = factory.create_product_catalog()
        items = self._voice_parser.parse(command.payload.text, catalog)
        create_request = MealCreateRequest(
            user_id=command.payload.user_id,
            meal_type=command.payload.meal_type,
            meal_date=command.payload.meal_date,
            original_text=command.payload.text,
            items=items,
        )
        meal = self._builder.from_request(create_request).build()
        saved = factory.create_meal_repository().add(meal)
        return saved.to_response()
