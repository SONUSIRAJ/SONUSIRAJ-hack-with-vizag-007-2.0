import requests
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_chatbox():
    user_context = {
        "name": "Sonu",
        "bmi": 22.9,
        "target_calories": 2800,
        "goal": "muscle_gain",
        "protein": 140
    }

    test_queries = [
        "Yo Vigo! How are you doing today?",
        "I feel so lazy today, I don't feel like working out.",
        "What should I eat after my workout for maximum gains?",
        "My knees hurt when I squat, what should I do?",
        "Will you marry me?"
    ]

    print("=" * 60)
    print("🤖 TESTING VIGOFIT AI COACH BEST FRIEND CHATBOX")
    print("=" * 60)

    for i, query in enumerate(test_queries, 1):
        print(f"\n--- TEST {i}: User: '{query}' ---")
        payload = {
            "user_id": "test_user_123",
            "message": query,
            "user_context": user_context
        }
        res = client.post("/api/ai/chat", json=payload)
        assert res.status_code == 200, f"Failed: {res.text}"
        reply = res.json().get("reply", "")
        print(f"🤖 Vigo (Best Friend AI):\n{reply}\n")
        print("-" * 60)

    print("\n✅ ALL CHATBOX BEST FRIEND TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    test_chatbox()
