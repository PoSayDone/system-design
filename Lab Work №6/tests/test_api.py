import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

LAB_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(LAB_DIR / "backend"))
os.environ["LAB6_DB_PATH"] = str(LAB_DIR / "backend" / "app" / "test_lab6.sqlite3")

db_file = Path(os.environ["LAB6_DB_PATH"])
if db_file.exists():
    db_file.unlink()

from app.database import Database
from app.main import app

USER_ID = str(uuid4())
MEAL_ID = None


@pytest.fixture(scope="module")
def client():
    Database().initialize()
    with TestClient(app) as test_client:
        yield test_client


def test_01_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_02_products_search(client):
    response = client.get("/api/v1/products", params={"q": "apple"})
    assert response.status_code == 200
    assert len(response.json()["products"]) >= 1


def test_03_create_meal(client):
    global MEAL_ID
    payload = {
        "user_id": USER_ID,
        "meal_type": "lunch",
        "meal_date": "2026-02-18",
        "original_text": "200g chicken and 150g rice",
        "items": [
            {
                "product_name": "chicken breast",
                "weight_grams": 200,
                "calories_per_100g": 165,
            },
            {
                "product_name": "rice",
                "weight_grams": 150,
                "calories_per_100g": 130,
            },
        ],
    }
    response = client.post("/api/v1/meals", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert UUID(data["id"])
    assert data["total_calories"] > 0
    MEAL_ID = data["id"]


def test_04_get_meal(client):
    response = client.get(f"/api/v1/meals/{MEAL_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == MEAL_ID


def test_05_list_meals(client):
    response = client.get(
        "/api/v1/meals",
        params={"user_id": USER_ID, "meal_date": "2026-02-18"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_06_day_summary(client):
    response = client.get(
        "/api/v1/reports/day-summary",
        params={"user_id": USER_ID, "meal_date": "2026-02-18"},
    )
    assert response.status_code == 200
    assert response.json()["total_calories"] > 0


def test_07_process_voice(client):
    payload = {
        "user_id": USER_ID,
        "text": "I ate chicken and apple",
        "meal_type": "dinner",
        "meal_date": "2026-02-18",
    }
    response = client.post("/api/v1/voice/process", json=payload)
    assert response.status_code == 201
    assert response.json()["total_calories"] > 0
    assert len(response.json()["items"]) == 2


def test_08_update_meal(client):
    payload = {
        "meal_type": "dinner",
        "original_text": "updated meal",
        "items": [
            {
                "product_name": "banana",
                "weight_grams": 120,
                "calories_per_100g": 89,
            }
        ],
    }
    response = client.put(f"/api/v1/meals/{MEAL_ID}", json=payload)
    assert response.status_code == 200
    assert response.json()["meal_type"] == "dinner"


def test_09_delete_meal(client):
    response = client.delete(f"/api/v1/meals/{MEAL_ID}")
    assert response.status_code == 204


def test_10_deleted_meal_not_found(client):
    response = client.get(f"/api/v1/meals/{MEAL_ID}")
    assert response.status_code == 404
