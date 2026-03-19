from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from .models import Meal, MealCreateRequest, MealItem, MealItemIn, MealType
from .strategies import CalorieCalculationStrategy, StandardCalorieStrategy


class MealBuilder:
    def __init__(
        self,
        strategy: CalorieCalculationStrategy | None = None,
    ) -> None:
        self._strategy = strategy or StandardCalorieStrategy()
        self.reset()

    def reset(self) -> None:
        self._meal_id = uuid4()
        self._user_id: UUID | None = None
        self._meal_type: MealType | None = None
        self._meal_date: date | None = None
        self._original_text = ""
        self._created_at = datetime.now(UTC)
        self._updated_at = self._created_at
        self._items: list[MealItem] = []

    def from_request(self, payload: MealCreateRequest) -> "MealBuilder":
        self.reset()
        self._user_id = payload.user_id
        self._meal_type = payload.meal_type
        self._meal_date = payload.meal_date
        self._original_text = payload.original_text
        for item in payload.items:
            self.add_item(item)
        return self

    def from_persisted(
        self,
        *,
        meal_id: UUID,
        user_id: UUID,
        meal_type: MealType,
        meal_date: date,
        original_text: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> "MealBuilder":
        self.reset()
        self._meal_id = meal_id
        self._user_id = user_id
        self._meal_type = meal_type
        self._meal_date = meal_date
        self._original_text = original_text
        self._created_at = created_at
        self._updated_at = updated_at
        return self

    def change_identity(self, meal_id: UUID) -> "MealBuilder":
        self._meal_id = meal_id
        return self

    def touch(self, updated_at: datetime) -> "MealBuilder":
        self._updated_at = updated_at
        return self

    def add_item(self, item: MealItemIn) -> "MealBuilder":
        self._items.append(
            MealItem(
                product_name=item.product_name,
                weight_grams=item.weight_grams,
                calories_per_100g=item.calories_per_100g,
                calories_total=self._strategy.calculate(
                    item.weight_grams, item.calories_per_100g
                ),
            )
        )
        return self

    def add_prebuilt_item(self, item: MealItem) -> "MealBuilder":
        self._items.append(item)
        return self

    def build(self) -> Meal:
        assert self._user_id is not None
        assert self._meal_type is not None
        assert self._meal_date is not None
        return Meal(
            id=self._meal_id,
            user_id=self._user_id,
            meal_type=self._meal_type,
            meal_date=self._meal_date,
            original_text=self._original_text,
            created_at=self._created_at,
            updated_at=self._updated_at,
            items=list(self._items),
        )
