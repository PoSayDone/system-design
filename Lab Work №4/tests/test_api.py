import sys
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

# Позволяет запускать тесты из каталога Lab Work №4 без настройки PYTHONPATH.
sys.path.append(str(Path(__file__).resolve().parents[1]))
from api.main import app

client = TestClient(app)
USER_ID = str(uuid4())
MEAL_ID = None


def test_01_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_02_products_search():
    response = client.get("/api/v1/products", params={"q": "apple"})
    assert response.status_code == 200
    assert len(response.json()["products"]) >= 1


def test_03_create_meal():
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
            {"product_name": "rice", "weight_grams": 150, "calories_per_100g": 130},
        ],
    }
    response = client.post("/api/v1/meals", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert UUID(data["id"])
    assert data["total_calories"] > 0
    MEAL_ID = data["id"]


def test_04_get_meal():
    response = client.get(f"/api/v1/meals/{MEAL_ID}")
    assert response.status_code == 200
    assert response.json()["id"] == MEAL_ID


def test_05_list_meals():
    response = client.get(
        "/api/v1/meals",
        params={"user_id": USER_ID, "meal_date": "2026-02-18"},
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_06_day_summary():
    response = client.get(
        "/api/v1/reports/day-summary",
        params={"user_id": USER_ID, "meal_date": "2026-02-18"},
    )
    assert response.status_code == 200
    assert response.json()["total_calories"] > 0


def test_07_process_voice():
    payload = {
        "user_id": USER_ID,
        "text": "I ate chicken and apple",
        "meal_type": "dinner",
        "meal_date": "2026-02-18",
    }
    response = client.post("/api/v1/voice/process", json=payload)
    assert response.status_code == 201
    assert response.json()["total_calories"] > 0


def test_08_update_meal():
    payload = {
        "meal_type": "dinner",
        "original_text": "updated meal",
        "items": [
            {"product_name": "banana", "weight_grams": 120, "calories_per_100g": 89}
        ],
    }
    response = client.put(f"/api/v1/meals/{MEAL_ID}", json=payload)
    assert response.status_code == 200
    assert response.json()["meal_type"] == "dinner"


def test_09_delete_meal():
    response = client.delete(f"/api/v1/meals/{MEAL_ID}")
    assert response.status_code == 204


def test_10_deleted_meal_not_found():
    response = client.get(f"/api/v1/meals/{MEAL_ID}")
    assert response.status_code == 404
