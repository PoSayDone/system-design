from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


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


@dataclass(slots=True)
class ProductInfo:
    product_name: str
    calories_per_100g: int


@dataclass(slots=True)
class MealItem:
    product_name: str
    weight_grams: int
    calories_per_100g: int
    calories_total: int


@dataclass(slots=True)
class Meal:
    id: UUID
    user_id: UUID
    meal_type: MealType
    meal_date: date
    original_text: str
    created_at: datetime
    updated_at: datetime
    items: list[MealItem] = field(default_factory=list)

    @property
    def total_calories(self) -> int:
        return sum(item.calories_total for item in self.items)

    def to_response(self) -> MealResponse:
        return MealResponse(
            id=self.id,
            user_id=self.user_id,
            meal_type=self.meal_type,
            meal_date=self.meal_date,
            original_text=self.original_text,
            total_calories=self.total_calories,
            items=[
                MealItemOut(
                    product_name=item.product_name,
                    weight_grams=item.weight_grams,
                    calories_per_100g=item.calories_per_100g,
                    calories_total=item.calories_total,
                )
                for item in self.items
            ],
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
