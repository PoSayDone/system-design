from __future__ import annotations

from abc import ABC, abstractmethod

from .models import MealItemIn
from .ports import ProductCatalog


class VoiceHandler(ABC):
    def __init__(self) -> None:
        self._next: VoiceHandler | None = None

    def set_next(self, handler: "VoiceHandler") -> "VoiceHandler":
        self._next = handler
        return handler

    def handle(self, text: str, catalog: ProductCatalog) -> list[MealItemIn]:
        items = self._try_handle(text, catalog)
        if self._next is None:
            return items
        return items + self._next.handle(text, catalog)

    @abstractmethod
    def _try_handle(self, text: str, catalog: ProductCatalog) -> list[MealItemIn]:
        raise NotImplementedError


class ChickenVoiceHandler(VoiceHandler):
    def _try_handle(self, text: str, catalog: ProductCatalog) -> list[MealItemIn]:
        if "chicken" not in text:
            return []
        product = catalog.get("chicken breast")
        assert product is not None
        return [
            MealItemIn(
                product_name=product.product_name,
                weight_grams=200,
                calories_per_100g=product.calories_per_100g,
            )
        ]


class AppleVoiceHandler(VoiceHandler):
    def _try_handle(self, text: str, catalog: ProductCatalog) -> list[MealItemIn]:
        if "apple" not in text:
            return []
        product = catalog.get("apple")
        assert product is not None
        return [
            MealItemIn(
                product_name=product.product_name,
                weight_grams=150,
                calories_per_100g=product.calories_per_100g,
            )
        ]


class FallbackVoiceHandler(VoiceHandler):
    def _try_handle(self, text: str, catalog: ProductCatalog) -> list[MealItemIn]:
        product = catalog.get("banana")
        assert product is not None
        return [
            MealItemIn(
                product_name=product.product_name,
                weight_grams=120,
                calories_per_100g=product.calories_per_100g,
            )
        ]


class KeywordVoiceParser:
    def __init__(self, root_handler: VoiceHandler) -> None:
        self._root_handler = root_handler

    def parse(self, text: str, catalog: ProductCatalog) -> list[MealItemIn]:
        text_lower = text.lower()
        items = self._root_handler.handle(text_lower, catalog)
        unique: dict[str, MealItemIn] = {item.product_name: item for item in items}
        if unique and not (
            len(unique) == 1
            and "banana" in unique
            and any(word in text_lower for word in ("apple", "chicken"))
        ):
            unique.pop("banana", None)
        return list(unique.values())


def build_voice_chain() -> KeywordVoiceParser:
    chicken = ChickenVoiceHandler()
    apple = AppleVoiceHandler()
    fallback = FallbackVoiceHandler()
    chicken.set_next(apple).set_next(fallback)
    return KeywordVoiceParser(chicken)
