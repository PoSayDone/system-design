from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Dict, List
from uuid import UUID

from fastapi import FastAPI, HTTPException, Query, Response, status

from .database import Database
from .facade import CalorieDiaryFacade
from .models import (
    DaySummaryResponse,
    MealCreateRequest,
    MealResponse,
    MealUpdateRequest,
    VoiceProcessRequest,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Database().initialize()
    yield


app = FastAPI(
    title="Calorie Voice Diary API",
    version="3.0.0",
    description="REST API с применением паттернов GoF и анализом GRASP",
    lifespan=lifespan,
)

facade = CalorieDiaryFacade()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/products")
def list_products(
    q: str | None = Query(default=None, max_length=100),
) -> Dict[str, List[Dict[str, int | str]]]:
    return facade.list_products(q)


@app.get("/api/v1/meals", response_model=List[MealResponse])
def list_meals(user_id: UUID, meal_date: date) -> List[MealResponse]:
    return facade.list_meals(user_id, meal_date)


@app.get("/api/v1/meals/{meal_id}", response_model=MealResponse)
def get_meal(meal_id: UUID) -> MealResponse:
    meal = facade.get_meal(meal_id)
    if meal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Meal not found",
        )
    return meal


@app.get("/api/v1/reports/day-summary", response_model=DaySummaryResponse)
def day_summary(user_id: UUID, meal_date: date) -> DaySummaryResponse:
    return facade.day_summary(user_id, meal_date)


@app.post(
    "/api/v1/meals",
    response_model=MealResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_meal(payload: MealCreateRequest) -> MealResponse:
    return facade.create_meal(payload)


@app.post(
    "/api/v1/voice/process",
    response_model=MealResponse,
    status_code=status.HTTP_201_CREATED,
)
def process_voice(payload: VoiceProcessRequest) -> MealResponse:
    return facade.process_voice(payload)


@app.put("/api/v1/meals/{meal_id}", response_model=MealResponse)
def update_meal(meal_id: UUID, payload: MealUpdateRequest) -> MealResponse:
    return facade.update_meal(meal_id, payload)


@app.delete("/api/v1/meals/{meal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meal(meal_id: UUID) -> Response:
    facade.delete_meal(meal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
