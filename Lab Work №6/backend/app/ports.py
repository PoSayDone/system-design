from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from uuid import UUID

from .models import Meal, ProductInfo


class MealRepository(ABC):
    @abstractmethod
    def add(self, meal: Meal) -> Meal:
        raise NotImplementedError

    @abstractmethod
    def update(self, meal: Meal) -> Meal:
        raise NotImplementedError

    @abstractmethod
    def delete(self, meal_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get(self, meal_id: UUID) -> Meal | None:
        raise NotImplementedError

    @abstractmethod
    def list_for_day(self, user_id: UUID, meal_date: date) -> list[Meal]:
        raise NotImplementedError

    @abstractmethod
    def day_summary(self, user_id: UUID, meal_date: date) -> tuple[int, int]:
        raise NotImplementedError


class ProductCatalog(ABC):
    @abstractmethod
    def list_products(self, query: str | None = None) -> list[ProductInfo]:
        raise NotImplementedError

    @abstractmethod
    def get(self, product_name: str) -> ProductInfo | None:
        raise NotImplementedError
