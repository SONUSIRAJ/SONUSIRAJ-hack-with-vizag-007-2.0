from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_routes():
    # Test Root
    res = client.get("/")
    assert res.status_code == 200, res.text
    print("Root endpoint OK:", res.json())

    # Test Onboard
    onboard_payload = {
        "name": "Sonu Siraj",
        "age": 24,
        "height": 175.0,
        "weight": 70.0,
        "biological_sex": "male",
        "goal": "muscle_gain",
        "activity_level": "moderate"
    }
    res = client.post("/api/users/onboard", json=onboard_payload)
    assert res.status_code == 200, res.text
    data = res.json()
    user_id = data["user"]["id"]
    print("Onboard endpoint OK:", data["user"]["name"], data["user"]["bmi"], data["user"]["target_calories"])

    # Test AI Chat
    chat_payload = {
        "user_id": user_id,
        "message": "What should I eat after my workout to build muscle?",
        "user_context": {
            "name": "Sonu Siraj",
            "bmi": 22.9,
            "target_calories": 2902,
            "goal": "muscle_gain",
            "protein": 140
        }
    }
    res = client.post("/api/ai/chat", json=chat_payload)
    assert res.status_code == 200, res.text
    print("AI Chat endpoint OK:", res.json()["reply"])

    # Test Auth Config
    res = client.get("/api/auth/config")
    assert res.status_code == 200, res.text
    print("Auth Config endpoint OK:", res.json())

    # Test Get Current User
    me_res = client.get(f"/api/auth/me?user_id={user_id}")
    assert me_res.status_code == 200, me_res.text
    assert me_res.json()["user"]["id"] == user_id
    print("Get Current User OK:", me_res.json()["user"]["name"])

    print("\nALL BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_routes()
