from __future__ import annotations

from abc import ABC, abstractmethod


class CalorieCalculationStrategy(ABC):
    @abstractmethod
    def calculate(self, weight_grams: int, calories_per_100g: int) -> int:
        raise NotImplementedError


class StandardCalorieStrategy(CalorieCalculationStrategy):
    def calculate(self, weight_grams: int, calories_per_100g: int) -> int:
        return round(weight_grams * calories_per_100g / 100)
