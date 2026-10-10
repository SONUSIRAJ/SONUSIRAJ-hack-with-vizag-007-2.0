import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.config import settings

# In-memory fallback store for offline / development testing without active Supabase credentials
_mock_db = {
    "users": {},
    "workout_logs": [],
    "routines": {},
    "chat_messages": []
}

supabase_client = None

if settings.SUPABASE_URL and not settings.SUPABASE_URL.startswith("https://xyz") and settings.SUPABASE_KEY:
    try:
        from supabase import create_client, Client
        supabase_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        print("Connected to Supabase successfully.")
    except Exception as e:
        print(f"Warning: Failed to connect to Supabase ({e}). Using local in-memory database fallback.")
else:
    print("Notice: Valid Supabase URL/Key not configured. Using local in-memory database fallback.")


# Helper operations with Supabase + Mock Fallback
def save_user(user_data: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(uuid.uuid4())
    user_record = {
        "id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        **user_data
    }
    
    if supabase_client:
        try:
            res = supabase_client.table("users").insert(user_record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase user insert failed: {e}. Falling back to local store.")
            
    _mock_db["users"][user_id] = user_record
    return user_record


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    if supabase_client:
        try:
            res = supabase_client.table("users").select("*").eq("id", user_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase get_user failed: {e}")
            
    return _mock_db["users"].get(user_id)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    clean_email = email.lower().strip()
    if supabase_client:
        try:
            res = supabase_client.table("users").select("*").eq("email", clean_email).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            print(f"Supabase get_user_by_email failed: {e}")
            
    for user in _mock_db["users"].values():
        if user.get("email", "").lower().strip() == clean_email:
            return user
    return None


def get_user_by_google_id(google_id: str) -> Optional[Dict[str, Any]]:
    if supabase_client:
        try:
            res = supabase_client.table("users").select("*").eq("google_id", google_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            print(f"Supabase get_user_by_google_id failed: {e}")
            
    for user in _mock_db["users"].values():
        if user.get("google_id") == google_id:
            return user
    return None


def update_user(user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if supabase_client:
        try:
            res = supabase_client.table("users").update(updates).eq("id", user_id).execute()
            if res.data and len(res.data) > 0:
                return res.data[0]
        except Exception as e:
            print(f"Supabase update_user failed: {e}")
            
    if user_id in _mock_db["users"]:
        _mock_db["users"][user_id].update(updates)
        return _mock_db["users"][user_id]
    return None


def upsert_google_user(google_profile: Dict[str, Any]) -> Dict[str, Any]:
    google_id = google_profile.get("google_id")
    email = (google_profile.get("email") or "").lower().strip()
    name = google_profile.get("name") or "Athlete"
    avatar_url = google_profile.get("avatar_url") or ""

    # 1. Try finding by google_id
    existing = get_user_by_google_id(google_id) if google_id else None
    
    # 2. Try finding by email
    if not existing and email:
        existing = get_user_by_email(email)

    if existing:
        # Update existing profile with latest avatar / google_id
        updates = {}
        if avatar_url and existing.get("avatar_url") != avatar_url:
            updates["avatar_url"] = avatar_url
        if google_id and not existing.get("google_id"):
            updates["google_id"] = google_id
        if email and not existing.get("email"):
            updates["email"] = email
        if updates:
            updated = update_user(existing["id"], updates)
            if updated:
                return updated
        return existing

    # 3. Create new user with Google profile & initial sensible biometrics
    user_id = str(uuid.uuid4())
    default_weight = 70.0
    default_height = 175.0
    bmi = round(default_weight / ((default_height / 100.0) ** 2), 1)

    user_record = {
        "id": user_id,
        "name": name,
        "email": email,
        "avatar_url": avatar_url,
        "google_id": google_id,
        "auth_provider": "google",
        "age": 24,
        "height": default_height,
        "weight": default_weight,
        "biological_sex": "male",
        "goal": "muscle_gain",
        "activity_level": "moderate",
        "workout_env": "gym",
        "bmi": bmi,
        "target_calories": 2400,
        "diet_preference": "non_veg",
        "target_pace": "moderate",
        "nutrition_plan": {
            "summary": f"Personalized high-protein plan for {name} targeted at 2,400 kcal/day.",
            "macros": {
                "protein_g": int(default_weight * 2),
                "carbs_g": 260,
                "fats_g": 65
            },
            "meal_ideas": [
                {"meal": "Breakfast", "recommendation": "Protein oatmeal with blueberries and almond butter"},
                {"meal": "Lunch", "recommendation": "Grilled chicken breast or paneer bowl with quinoa & greens"},
                {"meal": "Dinner", "recommendation": "Baked salmon or tofu stir fry with sweet potatoes & broccoli"}
            ],
            "hydration": f"Drink {round(default_weight * 0.045, 1)}L water daily"
        },
        "created_at": datetime.utcnow().isoformat()
    }

    if supabase_client:
        try:
            res = supabase_client.table("users").insert(user_record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase upsert_google_user failed: {e}. Falling back to mock store.")

    _mock_db["users"][user_id] = user_record
    return user_record


def log_workout(log_data: Dict[str, Any]) -> Dict[str, Any]:
    log_id = str(uuid.uuid4())
    log_record = {
        "id": log_id,
        "created_at": datetime.utcnow().isoformat(),
        **log_data
    }
    
    if supabase_client:
        try:
            res = supabase_client.table("workout_logs").insert(log_record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase log_workout failed: {e}. Falling back to local store.")
            
    _mock_db["workout_logs"].append(log_record)
    return log_record


def save_routine(user_id: str, environment: str, exercises: List[Dict[str, Any]]) -> Dict[str, Any]:
    routine_id = str(uuid.uuid4())
    routine_record = {
        "id": routine_id,
        "user_id": user_id,
        "environment": environment,
        "exercises": exercises,
        "created_at": datetime.utcnow().isoformat()
    }
    
    if supabase_client:
        try:
            res = supabase_client.table("routines").insert(routine_record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase save_routine failed: {e}")
            
    key = f"{user_id}_{environment}"
    _mock_db["routines"][key] = routine_record
    return routine_record


def save_chat_message(user_id: str, role: str, content: str) -> Dict[str, Any]:
    msg_id = str(uuid.uuid4())
    msg_record = {
        "id": msg_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "created_at": datetime.utcnow().isoformat()
    }

    if supabase_client:
        try:
            res = supabase_client.table("chat_messages").insert(msg_record).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            print(f"Supabase save_chat_message failed: {e}")

    _mock_db["chat_messages"].append(msg_record)
    return msg_record


def get_chat_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    if supabase_client:
        try:
            res = supabase_client.table("chat_messages").select("*").eq("user_id", user_id).order("created_at", desc=False).limit(limit).execute()
            if res.data:
                return res.data
        except Exception as e:
            print(f"Supabase get_chat_history failed: {e}")

    user_msgs = [m for m in _mock_db["chat_messages"] if m.get("user_id") == user_id]
    return user_msgs[-limit:]

