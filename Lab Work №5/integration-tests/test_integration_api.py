from uuid import UUID, uuid4
import os

import requests


BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
USER_ID = str(uuid4())
MEAL_ID = None


def test_01_health():
    response = requests.get(f"{BASE_URL}/health", timeout=10)
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_02_products_search():
    response = requests.get(f"{BASE_URL}/api/v1/products", params={"q": "apple"}, timeout=10)
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
            {
                "product_name": "rice",
                "weight_grams": 150,
                "calories_per_100g": 130,
            },
        ],
    }
    response = requests.post(f"{BASE_URL}/api/v1/meals", json=payload, timeout=10)
    assert response.status_code == 201
    data = response.json()
    assert UUID(data["id"])
    assert data["total_calories"] > 0
    MEAL_ID = data["id"]


def test_04_get_meal():
    response = requests.get(f"{BASE_URL}/api/v1/meals/{MEAL_ID}", timeout=10)
    assert response.status_code == 200
    assert response.json()["id"] == MEAL_ID


def test_05_list_meals():
    response = requests.get(
        f"{BASE_URL}/api/v1/meals",
        params={"user_id": USER_ID, "meal_date": "2026-02-18"},
        timeout=10,
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_06_day_summary():
    response = requests.get(
        f"{BASE_URL}/api/v1/reports/day-summary",
        params={"user_id": USER_ID, "meal_date": "2026-02-18"},
        timeout=10,
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
    response = requests.post(f"{BASE_URL}/api/v1/voice/process", json=payload, timeout=10)
    assert response.status_code == 201
    assert response.json()["total_calories"] > 0


def test_08_update_meal():
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
    response = requests.put(f"{BASE_URL}/api/v1/meals/{MEAL_ID}", json=payload, timeout=10)
    assert response.status_code == 200
    assert response.json()["meal_type"] == "dinner"


def test_09_delete_meal():
    response = requests.delete(f"{BASE_URL}/api/v1/meals/{MEAL_ID}", timeout=10)
    assert response.status_code == 204


def test_10_deleted_meal_not_found():
    response = requests.get(f"{BASE_URL}/api/v1/meals/{MEAL_ID}", timeout=10)
    assert response.status_code == 404
