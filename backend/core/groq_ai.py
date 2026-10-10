import json
import requests
import re
import random
from typing import Dict, Any, List, Optional
from core.config import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Models ordered: fastest/smallest first to stay within rate limits
GROQ_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


MASTER_SYSTEM_INSTRUCTION = """
# VIGOFIT AI TRAINER — PROFESSIONAL COACH & FRIEND

==================================================
1. YOUR IDENTITY & COMMUNICATION STYLE
==================================================
You are VigoFit AI Trainer, a professional, intelligent, supportive, and personalized fitness coach inside the VigoFit application.
Your personality combines:
- Professional fitness trainer & nutrition guide
- Supportive, friendly companion
- Personal accountability partner & practical problem solver

COMMUNICATION STYLE:
- Friendly, natural, and conversational.
- Professional but not robotic.
- Encouraging without being fake or excessively motivational.
- Use short, clear, easy-to-understand messages. Avoid long walls of text.
- Ask one logical group of questions at a time (1-3 questions max). Never overwhelm users with 20 questions in a single message.
- Use the user's name when available.
- Remember relevant information the user has already provided; do not repeatedly ask for known details.

==================================================
2. MOST IMPORTANT RULE — UNDERSTAND BEFORE PLANNING
==================================================
When a user asks for a plan or provides their college/work schedule, DO NOT immediately generate a full diet plan, workout plan, or daily routine schedule!
Follow this process:
1. Understand the user's daily routine & schedule.
2. Ask relevant clarification questions.
3. Collect fitness, nutrition, budget, and lifestyle preferences in conversational stages.
4. Check whether any essential information is missing.
5. Summarize what the user has told you.
6. Ask the user to confirm or correct the details.
7. ONLY AFTER CONFIRMATION, generate the personalized plan / schedule table.
8. Allow the user to edit the plan and update it based on feedback.

Never assume the user's wake-up time, sleep time, meal timings, free time, budget, or food preferences.

==================================================
3. CONVERSATIONAL INFORMATION COLLECTION STAGES
==================================================
STAGE 1 — DAILY ROUTINE:
Wake time, sleep time, sleep hours, home departure/return, college/work timings, travel time, meal timings, responsibilities, free time.

STAGE 2 — PERSONAL FITNESS PROFILE:
Age, height, current weight, gender, primary goal (muscle gain, weight loss, fat loss, muscle building, strength, endurance, general fitness, sports performance), experience (beginner, intermediate, advanced), workout location (gym, home, both), equipment, preferred days & duration, injuries/health concerns.

STAGE 3 — FOOD AND NUTRITION PREFERENCES:
Diet type (veg, non-veg, vegan, flexible), specific foods eaten (eggs, chicken, fish, mutton, paneer, dal, etc.), food dislikes/allergies, home-cooked vs restaurant, meal frequency & timings, portable packed meals for college/work, kitchen access, supplements, digestion concerns.

STAGE 4 — BUDGET:
Daily food budget (e.g., ₹100, ₹150, ₹200, ₹300+), monthly food budget (e.g., ₹3,000, ₹5,000, ₹7,000+), fitness-only vs all-meals budget, existing foods at home, willingness to spend extra, budget level (low-cost, moderate, flexible).

==================================================
4. FIXED SCHEDULE MANAGEMENT
==================================================
Treat college/work schedule (e.g., 7:30 AM – 6:30 PM) as a non-negotiable time block.
- Keep college/work hours blocked.
- Avoid scheduling workouts or heavy meals during unavailable class/work periods.
- Ask about actual break times (lunch break, free periods).
- Plan portable snacks/meals. Account for travel time.
- Schedule workouts before or after college based on user preference.

==================================================
5. FULL DAILY SCHEDULE FORMAT (ONLY AFTER CONFIRMATION)
==================================================
Once information is confirmed, provide a structured schedule table:
| Time | Activity | Details |
Include wake routine, pre-workout, breakfast, college/work blocks, breaks, lunch, evening snacks, post-workout, dinner, bedtime.

==================================================
6. ADAPTIVE COACHING & REAL LIFE ADJUSTMENTS
==================================================
When the user faces real-life disruptions:
- "I woke up late" / "I missed my workout": "No problem! Let me adjust today's schedule for you..."
- "I don't have chicken" / "Only ₹100 today": Offer cheap, high-protein local substitutes (eggs, curd, roasted chana, dal, soy chunks, paneer).
- "Feeling tired": Suggest a light session or recovery focus. Zero shaming or guilt.

==================================================
7. SAFETY & MEDICAL BOUNDARIES
==================================================
- Never diagnose medical conditions or prescribe medications.
- Recommend consulting a qualified healthcare professional for medical concerns.
- Distinguish estimates from verified measurements.

==================================================
8. STRICT DOMAIN CONTROL & TOPIC RELEVANCE
==================================================
You are a fitness coach first, NOT a programming teacher, coding tutor, or general academic instructor.
If the user asks an unrelated question (e.g., "What is C++?", "Teach me Python", "Help me with my Java exam", "Explain HTML", "Unrelated math/politics"):
- DO NOT provide detailed tutorials, code examples, syntax explanations, or lessons on unrelated subjects.
- Briefly identify the topic in 1 short friendly sentence, then naturally redirect to their fitness journey.
- Examples:
  • "What is C++? Explain in detail." -> "C++ is a programming language, but that's outside my main area as your fitness coach. I'm here to help you with fitness, nutrition, workouts, and health goals. Want to work on your fitness plan?"
  • "Teach me Python." -> "Python is used for programming, but I'm here to help you with your fitness journey. Want to plan your workout, nutrition, or recovery?"
  • "Help me prepare for Java exam." -> "I can help you with your fitness and nutrition goals, but exam preparation is outside my coaching focus. How is your workout routine going today?"

ALLOWED TECHNICAL EXPLANATIONS:
- You may explain technical or scientific topics ONLY when directly relevant to fitness (e.g., how calories/macros work, protein synthesis, sleep recovery, heart rate zones, how AI camera pose detection tracks exercise form).
"""



def call_groq_api(messages: List[Dict[str, str]], json_mode: bool = False, temperature: float = 0.7) -> Optional[str]:
    """
    Calls the Groq API with model fallback and rate-limit backoff.
    """
    import time
    api_key = settings.GROQ_API_KEY.strip()
    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    for i, model in enumerate(GROQ_MODELS):
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1200
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            res = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    if content and content.strip():
                        return content.strip()
            elif res.status_code == 429:
                # Rate limited — wait briefly before next model attempt
                print(f"Groq API model {model} rate limited (429), trying next...")
                if i < len(GROQ_MODELS) - 1:
                    time.sleep(1.0)
            else:
                print(f"Groq API model {model} returned status {res.status_code}: {res.text[:150]}")
        except Exception as e:
            print(f"Groq API connection error with model {model}: {e}")

    return None


def generate_groq_full_brain_plan(
    name: str, age: int, height: float, weight: float, sex: str,
    goal: str, activity_level: str, diet: str = "non_veg", env: str = "gym",
    equipment: list = None
) -> Dict[str, Any]:
    """
    Generates a full AI plan including Diet, Workout, Sleep Cycle, Daily Guidance, and Data Analysis via Groq AI.
    """
    system_prompt = MASTER_SYSTEM_INSTRUCTION + "\nReturn strictly valid JSON containing: health_analysis, diet_plan, workout_plan, sleep_cycle, and daily_guidance."

    user_prompt = f"""Generate a master fitness blueprint for:
- Name: {name}
- Age: {age} years
- Height: {height} cm
- Weight: {weight} kg
- Biological Sex: {sex}
- Primary Goal: {goal}
- Activity Level: {activity_level}
- Diet Preference: {diet}
- Environment: {env}
- Available Equipment: {', '.join(equipment) if equipment else 'None (Bodyweight only)'}

Return ONLY valid JSON matching this exact structure:
{{
  "health_analysis": {{
    "bmi": 22.5,
    "bmr_kcal": 1650,
    "tdee_kcal": 2400,
    "target_calories_kcal": 2200,
    "recovery_readiness_score": 94,
    "health_summary": "Biomechanical and metabolic baseline assessment."
  }},
  "diet_plan": {{
    "summary": "Structured high-protein nutrition plan aligned with target calories.",
    "macros": {{
      "protein_g": {int(weight * 2)},
      "carbs_g": 220,
      "fats_g": 65
    }},
    "meal_ideas": [
      {{"meal": "Breakfast", "time": "7:30 AM", "recommendation": "Protein oats with chia seeds, banana & 3 egg whites", "cal": 480}},
      {{"meal": "Lunch", "time": "1:00 PM", "recommendation": "Grilled chicken breast or paneer with quinoa & roasted broccoli", "cal": 620}},
      {{"meal": "Dinner", "time": "7:30 PM", "recommendation": "Baked salmon or tofu with sweet potato & asparagus", "cal": 580}},
      {{"meal": "Snack", "time": "4:30 PM", "recommendation": "Greek yogurt or whey protein shake with almond butter", "cal": 320}}
    ],
    "hydration": "Drink {round(weight * 0.045, 1)}L water daily."
  }},
  "workout_plan": {{
    "summary": "AI tailored workout routine targeting key muscle groups.",
    "exercises": [
      {{
        "id": "squats",
        "name": "Squats (Goblet / Barbell / Bodyweight)",
        "target_sets": 3,
        "target_reps": 12,
        "angle_key": "hip_knee_ankle",
        "description": "Break at hips first, keep chest high, squat to 90 degrees."
      }},
      {{
        "id": "pushups",
        "name": "Push-ups (Standard / Weighted)",
        "target_sets": 3,
        "target_reps": 12,
        "angle_key": "shoulder_elbow_wrist",
        "description": "Rigid plank core, flex elbows to 90 degrees, press up."
      }},
      {{
        "id": "bicep_curls",
        "name": "Bicep Curls (DB / Cable / Band)",
        "target_sets": 3,
        "target_reps": 12,
        "angle_key": "shoulder_elbow_wrist",
        "description": "Pin elbows to torso, flex to 40 degrees peak tension."
      }}
    ]
  }},
  "sleep_cycle": {{
    "recommended_sleep_hours": 8.0,
    "bedtime": "10:30 PM",
    "wake_time": "6:30 AM",
    "rem_deep_target": "3.5 hours (Deep + REM sleep)",
    "wind_down_routine": [
      "No blue light 45 min before sleep",
      "Magnesium glycinate or herbal tea",
      "5 min 4-4-4 box breathing"
    ],
    "sleep_score_target": 92
  }},
  "daily_guidance": {{
    "morning": "Wake 6:30 AM, hydrate 500ml water, High-Protein Breakfast (7:30 AM)",
    "afternoon": "Balanced Lunch (1:00 PM), light 10m walk, hydration check",
    "evening": "AI Workout Session (6:00 PM), Post-workout shake (7:00 PM), Dinner (7:30 PM)",
    "night": "Wind-down routine (9:45 PM), Bedtime (10:30 PM)"
  }}
}}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response_text = call_groq_api(messages, json_mode=True, temperature=0.5)

    if response_text:
        try:
            return json.loads(response_text)
        except Exception as err:
            print(f"Error parsing Groq JSON response: {err}")

    # Fallback high-fidelity local AI generation engine
    height_m = height / 100.0
    bmi = round(weight / (height_m * height_m), 1) if height_m > 0 else 22.5
    bmr = round((10 * weight + 6.25 * height - 5 * age + (5 if sex == "male" else -161)))
    act_map = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "extra_active": 1.9}
    tdee = round(bmr * act_map.get(activity_level.lower(), 1.55))
    target_cals = max(1200, tdee - 400) if "loss" in goal.lower() else (tdee + 300 if "gain" in goal.lower() else tdee)
    protein_g = int(weight * 2)
    rem_cals = max(0, target_cals - protein_g * 4)
    carbs_g = int((rem_cals * 0.58) / 4)
    fats_g = int((rem_cals * 0.42) / 9)
    hydration_l = round(weight * 0.045, 1)

    # Diet specifics for fallback
    diet_map = {
        "veg": ["Paneer tikka with quinoa", "Tofu scramble with spinach", "Lentil soup with mixed greens", "Greek yogurt with berries"],
        "non_veg": ["Grilled chicken with broccoli", "Salmon with sweet potato", "Turkey meatballs with zucchini noodles", "Eggs with whole grain toast"]
    }
    meals = diet_map.get(diet.lower(), diet_map["non_veg"])

    return {
        "health_analysis": {
            "bmi": bmi,
            "bmr_kcal": bmr,
            "tdee_kcal": tdee,
            "target_calories_kcal": target_cals,
            "recovery_readiness_score": 94,
            "health_summary": f"Optimal metabolic baseline for {name} ({age} y/o). Your TDEE is {tdee} kcal with target set to {target_cals} kcal for {goal.replace('_', ' ')}."
        },
        "diet_plan": {
            "summary": f"Personalized 2g/kg protein blueprint targeting {target_cals} kcal/day ({diet}).",
            "macros": {
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fats_g": fats_g
            },
            "meal_ideas": [
                {"meal": "Breakfast", "time": "7:30 AM", "recommendation": meals[3] if len(meals) > 3 else "Protein oats", "cal": int(target_cals * 0.25)},
                {"meal": "Lunch", "time": "1:00 PM", "recommendation": meals[0], "cal": int(target_cals * 0.35)},
                {"meal": "Dinner", "time": "7:30 PM", "recommendation": meals[1], "cal": int(target_cals * 0.30)},
                {"meal": "Snack", "time": "4:30 PM", "recommendation": meals[2], "cal": int(target_cals * 0.10)}
            ],
            "hydration": f"Drink {hydration_l}L water daily."
        },
        "workout_plan": {
            "summary": f"Targeted 3-exercise routine optimized for {env} environment using {', '.join(equipment) if equipment else 'bodyweight'}.",
            "exercises": [
                {
                    "id": "squats",
                    "name": "Goblet Squats" if equipment and ("Dumbbells" in equipment or "Kettlebells" in equipment) else ("Barbell Squats" if equipment and "Barbell" in equipment else "Bodyweight Squats"),
                    "target_sets": 3,
                    "target_reps": 12 if env == "gym" else 15,
                    "angle_key": "hip_knee_ankle",
                    "description": "Break at hips first, keep chest high, squat to 90 degrees."
                },
                {
                    "id": "pushups",
                    "name": "Incline Push-ups" if env == "gym" else "Standard Push-ups",
                    "target_sets": 3,
                    "target_reps": 10 if env == "gym" else 12,
                    "angle_key": "shoulder_elbow_wrist",
                    "description": "Rigid plank core, flex elbows to 90 degrees, press up."
                },
                {
                    "id": "bicep_curls",
                    "name": "Dumbbell Bicep Curls" if equipment and "Dumbbells" in equipment else ("Cable Curls" if equipment and "Cable Machine" in equipment else "Resistance Band Curls"),
                    "target_sets": 3,
                    "target_reps": 12 if env == "gym" else 15,
                    "angle_key": "shoulder_elbow_wrist",
                    "description": "Pin elbows to torso, flex to 40 degrees peak tension."
                }
            ]
        },
        "sleep_cycle": {
            "recommended_sleep_hours": 8.0,
            "bedtime": "10:30 PM",
            "wake_time": "6:30 AM",
            "rem_deep_target": "3.5 hours (Deep + REM sleep)",
            "wind_down_routine": [
                "Dim lights 1 hour before bed to boost melatonin",
                "Hydrate with 250ml electrolyte/herbal water",
                "5 min box breathing (4s inhale, 4s hold, 4s exhale)"
            ],
            "sleep_score_target": 92
        },
        "daily_guidance": {
            "morning": "Wake 6:30 AM, hydrate 500ml water, High-Protein Breakfast (7:30 AM)",
            "afternoon": "Balanced Lunch (1:00 PM), light 10m walk, hydration check",
            "evening": "AI Workout Session (6:00 PM), Post-workout shake (7:00 PM), Dinner (7:30 PM)",
            "night": "Wind-down routine (9:45 PM), Bedtime (10:30 PM)"
        }
    }

def groq_chat_reply(message: str, history: List[Dict[str, str]], context: Dict[str, Any]) -> str:
    """
    Handles conversational chat requests using Groq AI and VIGO FIT Master Instructions.
    Follows natural, friendly, concise conversational guidelines.
    """
    name = context.get("name", "Athlete")
    age = context.get("age", 24)
    height = context.get("height", 175)
    weight = context.get("weight", 70)
    bmi = context.get("bmi", 22.5)
    cals = context.get("target_calories", 2200)
    goal = context.get("goal", "muscle_gain")
    protein = context.get("protein", 140)
    diet = context.get("diet", "non_veg")
    activity_level = context.get("activity_level", "moderate")

    msg_lower = message.lower().strip()

    # Section 5: Simple & Repetitive Greeting Handler
    simple_greetings = ["hi", "hello", "hey", "hlo", "hy", "yo", "good morning", "good evening", "what's up", "whats up", "start", "let's begin", "lets begin"]
    
    greetings_pool = [
        f"Yo {name}! 💪 Great to see you. How's your day going — locked in on gym, healthcare, or grinding on your career today?",
        f"Hey {name}! Your AI coach & best friend reporting for duty. What are we optimizing today — workout form, nutrition, or recovery?",
        f"Welcome back {name}! 🚀 Health is wealth, and so is career focus. What's our main priority right now — gym, diet, or productivity?",
        f"Hey {name}! Ready to crush it. What do you need help with today?"
    ]

    playful_spam_responses = [
        f"Are you joking with me, {name}? 😂 'Hi' received loud and clear! Enough warm-ups — as your friend and coach, I want to see you win in the gym, in your healthcare, AND in your career! 🚀 So what's the game plan today — workout, meal prep, or career focus?",
        f"Haha {name}, are you testing my echo? 😜 I hear you! But listen — real champions don't just say 'hi' repeatedly, they take action. How's your gym energy, your health, and your career focus holding up today?",
        f"Yo {name}! Are you joking around? 😂 I'm here for you 24/7 as your best friend, gym partner, and career hype-man. Stop spamming greetings and let's lock in! What are we focusing on right now?"
    ]

    if msg_lower in simple_greetings or any(msg_lower == g for g in simple_greetings):
        # Inspect recent history for previous simple greetings
        recent_user_msgs = [m.get("content", "").lower().strip() for m in (history or []) if m.get("role") == "user"]
        greeting_count = sum(1 for m in recent_user_msgs[-3:] if m in simple_greetings or any(m == g for g in simple_greetings))
        
        if greeting_count >= 1:
            return random.choice(playful_spam_responses)
        return random.choice(greetings_pool)

    # Section 8: Unrelated Topic Redirection Guard (Coding / Academic / Non-fitness)
    coding_patterns = [
        r"\bwhat is c\+\+\b", r"\bteach me c\+\+\b", r"\bc\+\+ in detail\b", r"\bc\+\+\b",
        r"\bwhat is python\b", r"\bteach me python\b", r"\bpython tutorial\b",
        r"\bwhat is java\b", r"\bjava exam\b", r"\bjavascript\b", r"\bhtml\b", r"\bcss\b",
        r"\bweb development\b", r"\bteach me coding\b", r"\bprogramming tutorial\b"
    ]
    if any(re.search(pat, msg_lower) for pat in coding_patterns):
        if "c++" in msg_lower:
            return "C++ is a programming language, but that's outside my main area as your fitness coach. I'm here to help you with fitness, nutrition, workouts, and health goals. Want to work on your fitness plan?"
        elif "python" in msg_lower:
            return "Python is used for programming, but I'm here to help you with your fitness journey. Want to plan your workout, nutrition, or recovery?"
        elif "java" in msg_lower:
            return "I can help you with your fitness and nutrition goals, but exam preparation is outside my coaching focus. How is your workout routine going today?"
        else:
            return "That topic is outside my primary focus as your fitness coach. I'm here to help you with fitness, nutrition, workouts, and health goals. What fitness goal are we focusing on today?"

    system_instruction = f"""{MASTER_SYSTEM_INSTRUCTION}

CURRENT USER CONTEXT (FROM USER SETTINGS PANEL):
- Name: {name}
- Age: {age} years
- Height: {height} cm
- Weight: {weight} kg
- BMI: {bmi}
- Dietary Preference: {diet}
- Activity Level: {activity_level}
- Primary Goal: {goal.replace('_', ' ')}
- Daily Calorie Target: {cals} kcal
- Daily Protein Target: {protein}g

SPECIAL CONVERSATIONAL INSTRUCTIONS:
- Directly answer what the user asked.
- REPETITIVE GREETINGS RULE: If the user repeatedly says "hi", "hey", or spams simple greetings multiple times in a row, call it out playfully ("Are you joking with me? 😂"). Then act like a real best friend who cares about their gym gains, overall healthcare, and career/future focus. Encourage them to stop wasting time and lock in!
- Keep responses short (1-4 sentences for simple questions).
- Use the user's settings (height: {height}cm, weight: {weight}kg, age: {age}, goal: {goal.replace('_', ' ')}) to personalize answers without reading out all raw numbers unless requested.
- DOMAIN CONTROL: You are a fitness coach first, NOT a programming teacher or coding tutor. If asked about C++, Python, Java, HTML, CSS, or coding, briefly identify it in 1 short sentence, DO NOT teach or write code, and redirect naturally to their fitness goals.
- Speak naturally like a supportive friend and certified coach.
"""

    messages = [{"role": "system", "content": system_instruction}]

    for msg in history[-8:]:
        role = "user" if msg.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": msg.get("content", "")})

    messages.append({"role": "user", "content": message})

    response_text = call_groq_api(messages, json_mode=False, temperature=0.7)
    if response_text:
        return response_text

    # Spec-compliant Fallbacks if API is unavailable
    if msg_lower in simple_greetings:
        recent_user_msgs = [m.get("content", "").lower().strip() for m in (history or []) if m.get("role") == "user"]
        greeting_count = sum(1 for m in recent_user_msgs[-3:] if m in simple_greetings or any(m == g for g in simple_greetings))
        if greeting_count >= 1:
            return random.choice(playful_spam_responses)
        return random.choice(greetings_pool)

    if any(m in msg_lower for m in ["lazy", "motivated", "motivation", "tired", "giving up", "cant"]):
        return (
            f"That happens 😄 Don't force a heavy workout if you're exhausted, {name}. "
            f"Try a light session or take a recovery day. Are you physically tired, or just low on motivation today?"
        )

    if any(m in msg_lower for m in ["missed", "skip", "skipped"]):
        return (
            f"No stress! One missed workout won't destroy your progress 💪 "
            f"Just get back to your routine tomorrow. What stopped you today?"
        )

    if any(m in msg_lower for m in ["junk", "cheat meal", "pizza", "burger", "cake"]):
        return (
            f"Relax, one meal won't ruin your progress 😄 "
            f"Just get back to your normal routine at the next meal. No need to punish yourself with extra workouts!"
        )

    if "sleep" in msg_lower or "bedtime" in msg_lower or "wake" in msg_lower or "rest" in msg_lower:
        return (
            f"🌙 A consistent sleep routine makes a huge difference, {name}.\n\n"
            f"Aim for 7.5–8 hours of sleep. Try dimming screens 45 mins before bed to recover better for tomorrow!"
        )

    if "protein" in msg_lower or "diet" in msg_lower or "eat" in msg_lower or "meal" in msg_lower:
        return (
            f"For your {goal.replace('_', ' ')} goal, focus on protein + carbs in your meals 💪\n\n"
            f"Good options: eggs, chicken, paneer, dal, oats, curd, or rice. What foods do you usually have at home?"
        )

    if "workout" in msg_lower or "exercise" in msg_lower or "squat" in msg_lower or "pushup" in msg_lower:
        return (
            f"Try starting with bodyweight squats or push-ups 💪\n\n"
            f"Focus on controlled form over speed (e.g. 3 sets of 10–12 reps). How many days per week are you planning to train?"
        )

    return (
        f"Hey {name}! I'm here to help with your workouts, diet, sleep, or recovery. What specifically do you want to work on today?"
    )


def extract_profile_from_chat(conversation_history: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    """
    Scans the chat conversation history and extracts any user profile details
    mentioned by the user (name, age, height, weight, sex, goal, activity_level, diet).
    Returns ONLY the fields that were explicitly mentioned — partial updates are OK.
    Returns None if extraction fails completely.
    """
    system_prompt = """You are a data extraction assistant for the VigoFit fitness app.
Your job is to carefully read the conversation history and extract ANY user profile information
that the user has explicitly mentioned.

EXTRACT ONLY fields that the user clearly stated. Do NOT guess or invent values.

Return ONLY valid JSON with these possible keys (include a key ONLY if the user mentioned it):
{
  "name": "string — the user's name",
  "age": number — the user's age in years,
  "height": number — height in cm,
  "weight": number — weight in kg,
  "biological_sex": "male" or "female",
  "goal": "weight_loss" or "muscle_gain" or "maintenance" or "fat_loss" or "strength" or "endurance" or "general_fitness",
  "activity_level": "sedentary" or "light" or "moderate" or "active" or "extra_active",
  "diet": "veg" or "non_veg" or "vegan" or "flexible"
}

RULES:
- If the user says "I'm 22", set "age": 22
- If the user says "my name is Sonu", set "name": "Sonu"
- If the user says "I weigh 75 kg" or "75kg", set "weight": 75
- If the user says "I'm 180 cm" or "180cm tall" or "5'11", convert to cm and set "height"
- If the user says "I want to lose weight", set "goal": "weight_loss"
- If the user says "I want to build muscle" or "bulk up", set "goal": "muscle_gain"
- If the user says "I'm vegetarian" or "I don't eat meat", set "diet": "veg"
- If the user says "I'm very active" or "I work out daily", set "activity_level": "active"
- Convert feet/inches to cm if needed (1 foot = 30.48 cm, 1 inch = 2.54 cm)
- Convert lbs to kg if needed (1 lb = 0.4536 kg)
- If NO profile information is found at all, return: {"no_data": true}
- Return ONLY valid JSON, nothing else.
"""

    # Build a compact version of the conversation for extraction
    chat_text = ""
    for msg in conversation_history[-20:]:  # Last 20 messages max
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content:
            chat_text += f"{role}: {content}\n"

    if not chat_text.strip():
        return None

    user_prompt = f"""Extract user profile information from this conversation:

{chat_text}

Return ONLY valid JSON with the extracted fields."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    response_text = call_groq_api(messages, json_mode=True, temperature=0.1)

    if response_text:
        try:
            data = json.loads(response_text)
            if data.get("no_data"):
                return None
            # Clean and validate extracted fields
            cleaned = {}
            if "name" in data and isinstance(data["name"], str) and data["name"].strip():
                cleaned["name"] = data["name"].strip()
            if "age" in data:
                try:
                    age_val = int(data["age"])
                    if 10 <= age_val <= 120:
                        cleaned["age"] = age_val
                except (ValueError, TypeError):
                    pass
            if "height" in data:
                try:
                    h_val = float(data["height"])
                    if 100 <= h_val <= 250:
                        cleaned["height"] = h_val
                except (ValueError, TypeError):
                    pass
            if "weight" in data:
                try:
                    w_val = float(data["weight"])
                    if 30 <= w_val <= 300:
                        cleaned["weight"] = w_val
                except (ValueError, TypeError):
                    pass
            if "biological_sex" in data and data["biological_sex"] in ("male", "female"):
                cleaned["biological_sex"] = data["biological_sex"]
            if "goal" in data:
                goal_map = {
                    "weight_loss": "weight_loss", "fat_loss": "weight_loss",
                    "muscle_gain": "muscle_gain", "bulk": "muscle_gain", "bulking": "muscle_gain",
                    "maintenance": "maintenance", "maintain": "maintenance",
                    "strength": "muscle_gain", "endurance": "maintenance",
                    "general_fitness": "maintenance",
                }
                cleaned_goal = goal_map.get(data["goal"], data["goal"])
                if cleaned_goal in ("weight_loss", "muscle_gain", "maintenance"):
                    cleaned["goal"] = cleaned_goal
            if "activity_level" in data and data["activity_level"] in ("sedentary", "light", "moderate", "active", "extra_active"):
                cleaned["activity_level"] = data["activity_level"]
            if "diet" in data:
                diet_map = {
                    "veg": "veg", "vegetarian": "veg",
                    "non_veg": "non_veg", "nonveg": "non_veg", "non-veg": "non_veg",
                    "vegan": "vegan",
                    "flexible": "flexible", "mixed": "flexible",
                }
                cleaned_diet = diet_map.get(data["diet"], data["diet"])
                if cleaned_diet in ("veg", "non_veg", "vegan", "flexible"):
                    cleaned["diet"] = cleaned_diet

            return cleaned if cleaned else None
        except (json.JSONDecodeError, Exception) as err:
            print(f"Error parsing profile extraction JSON: {err}")
            return None

    return None

