from __future__ import annotations

import sqlite3

from .models import ProductInfo
from .ports import ProductCatalog


class StaticNutritionProvider:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def fetch_rows(self, query: str | None = None) -> list[sqlite3.Row]:
        if query:
            return self._conn.execute(
                """
                SELECT name, calories_per_100g
                FROM products
                WHERE LOWER(name) LIKE LOWER(?)
                ORDER BY name
                """,
                (f"%{query}%",),
            ).fetchall()
        return self._conn.execute(
            "SELECT name, calories_per_100g FROM products ORDER BY name"
        ).fetchall()

    def fetch_one(self, product_name: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT name, calories_per_100g FROM products WHERE LOWER(name) = LOWER(?)",
            (product_name,),
        ).fetchone()


class NutritionCatalogAdapter(ProductCatalog):
    def __init__(self, provider: StaticNutritionProvider) -> None:
        self._provider = provider

    def list_products(self, query: str | None = None) -> list[ProductInfo]:
        return [
            ProductInfo(
                product_name=row["name"],
                calories_per_100g=row["calories_per_100g"],
            )
            for row in self._provider.fetch_rows(query)
        ]

    def get(self, product_name: str) -> ProductInfo | None:
        row = self._provider.fetch_one(product_name)
        if not row:
            return None
        return ProductInfo(
            product_name=row["name"],
            calories_per_100g=row["calories_per_100g"],
        )


class CachedProductCatalogProxy(ProductCatalog):
    def __init__(self, inner: ProductCatalog) -> None:
        self._inner = inner
        self._cache: dict[str | None, list[ProductInfo]] = {}
        self._single_cache: dict[str, ProductInfo | None] = {}

    def list_products(self, query: str | None = None) -> list[ProductInfo]:
        if query not in self._cache:
            self._cache[query] = self._inner.list_products(query)
        return list(self._cache[query])

    def get(self, product_name: str) -> ProductInfo | None:
        key = product_name.lower()
        if key not in self._single_cache:
            self._single_cache[key] = self._inner.get(product_name)
        return self._single_cache[key]
