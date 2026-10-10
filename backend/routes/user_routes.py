from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from database.db import save_user, get_user, save_routine
from core.groq_ai import generate_groq_full_brain_plan

router = APIRouter(prefix="/api/users", tags=["users"])

class OnboardRequest(BaseModel):
    name: Optional[str] = Field("Athlete", description="User's full name")
    age: int = Field(..., ge=10, le=120)
    height: float = Field(..., ge=50, le=250, description="Height in cm")
    weight: float = Field(..., ge=20, le=300, description="Weight in kg")
    biological_sex: str = Field(..., description="'male' or 'female'")
    goal: str = Field(..., description="'weight_loss', 'maintenance', or 'muscle_gain'")
    activity_level: Optional[str] = Field("moderate", description="Activity level string")
    diet: Optional[str] = Field("non_veg", description="'veg' or 'non_veg'")
    workout_env: Optional[str] = Field("gym", description="'gym' or 'home'")
    equipment: Optional[List[str]] = None
    user_id: Optional[str] = None

@router.post("/onboard")
def onboard_user(req: OnboardRequest):
    user_name = req.name.strip() if req.name and req.name.strip() else "Athlete"
    env = req.workout_env or "gym"

    # Generate complete Groq AI Plan: Diet, Workout, Sleep Cycle, and Health Analysis
    groq_master_plan = generate_groq_full_brain_plan(
        name=user_name,
        age=req.age,
        height=req.height,
        weight=req.weight,
        sex=req.biological_sex,
        goal=req.goal,
        activity_level=req.activity_level or "moderate",
        diet=req.diet or "non_veg",
        env=env,
        equipment=req.equipment
    )

    health_analysis = groq_master_plan.get("health_analysis", {})
    nutrition_plan = groq_master_plan.get("diet_plan", {})
    workout_plan = groq_master_plan.get("workout_plan", {})
    sleep_cycle = groq_master_plan.get("sleep_cycle", {})

    user_payload = {
        "name": user_name,
        "age": req.age,
        "height": req.height,
        "weight": req.weight,
        "biological_sex": req.biological_sex,
        "goal": req.goal,
        "activity_level": req.activity_level or "moderate",
        "diet": req.diet or "non_veg",
        "workout_env": env,
        "equipment": req.equipment or [],
        "bmi": health_analysis.get("bmi", round(req.weight / ((req.height/100)**2), 1)),
        "target_calories": health_analysis.get("target_calories_kcal", 2200),
        "nutrition_plan": nutrition_plan,
        "workout_plan": workout_plan,
        "sleep_cycle": sleep_cycle,
        "health_analysis": health_analysis,
        "ai_engine": "Groq LLaMA-3.3-70B AI Brain"
    }

    if req.user_id:
        from database.db import update_user
        saved_user = update_user(req.user_id, user_payload)
        if not saved_user:
            # Fallback if user not found
            saved_user = save_user(user_payload)
    else:
        saved_user = save_user(user_payload)

    return {
        "status": "success",
        "user": saved_user
    }

@router.get("/{user_id}/master-plan")
def get_user_master_plan(
    user_id: str,
    name: str = Query("Athlete"),
    age: int = Query(25),
    height: float = Query(175.0),
    weight: float = Query(70.0),
    sex: str = Query("male"),
    goal: str = Query("muscle_gain"),
    activity: str = Query("moderate"),
    env: str = Query("gym")
):
    plan = generate_groq_full_brain_plan(
        name=name, age=age, height=height, weight=weight,
        sex=sex, goal=goal, activity_level=activity, env=env
    )
    return {
        "status": "success",
        "master_plan": plan
    }

@router.get("/{user_id}/routine")
def get_user_routine(user_id: str, environment: str = Query("home", description="'home' or 'gym'")):
    env_clean = environment.lower()

    if env_clean == "gym":
        exercises = [
            {
                "id": "squats",
                "name": "Barbell / Goblet Squats",
                "target_sets": 3,
                "target_reps": 12,
                "angle_key": "hip_knee_ankle",
                "description": "Keep chest high, break at hips first, squat to 90 degrees."
            },
            {
                "id": "pushups",
                "name": "Incline / Weighted Push-ups",
                "target_sets": 3,
                "target_reps": 10,
                "angle_key": "shoulder_elbow_wrist",
                "description": "Lower chest down to 90 degree elbow bend, drive up explosively."
            },
            {
                "id": "bicep_curls",
                "name": "Dumbbell Bicep Curls",
                "target_sets": 3,
                "target_reps": 12,
                "angle_key": "shoulder_elbow_wrist",
                "description": "Pin elbows to ribs, flex up to 40 degrees, extend back fully."
            }
        ]
    else:
        exercises = [
            {
                "id": "squats",
                "name": "Bodyweight Squats",
                "target_sets": 3,
                "target_reps": 15,
                "angle_key": "hip_knee_ankle",
                "description": "Feet shoulder-width apart, sink hips back, keep knees tracking over toes."
            },
            {
                "id": "pushups",
                "name": "Standard Push-ups",
                "target_sets": 3,
                "target_reps": 12,
                "angle_key": "shoulder_elbow_wrist",
                "description": "Maintain a rigid plank core, lower chest near floor, push back up."
            },
            {
                "id": "bicep_curls",
                "name": "Resistance Curls",
                "target_sets": 3,
                "target_reps": 15,
                "angle_key": "shoulder_elbow_wrist",
                "description": "Flex arm from 160 degrees down to 40 degrees elbow flexion."
            }
        ]

    saved_routine = save_routine(user_id, env_clean, exercises)
    return {
        "user_id": user_id,
        "environment": env_clean,
        "routine": saved_routine
    }
