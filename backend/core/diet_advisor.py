from typing import Dict, Any, List, Optional

def evaluate_diet_recommendation(
    food_data: Dict[str, Any],
    serving_g: float,
    user_profile: Dict[str, Any],
    daily_intake: Dict[str, Any],
    daily_targets: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Personalized AI Diet Recommendation Engine:
    Evaluates identified food against user biometrics, fitness goal, dietary restrictions,
    recorded daily intake, and daily targets.

    Returns:
      - recommendation_label: 'GOOD FIT' | 'FITS WITH ADJUSTMENTS' | 'LESS SUITABLE RIGHT NOW'
      - badge_color: hex string for UI styling
      - explanation: plain language, supportive explanation grounded in verified nutrition
      - portion_advice: optional suggested portion weight (g)
      - warnings: list of dietary preference/conflict warnings
      - impact_preview: before vs after comparison for cals, protein, carbs, fat
    """
    ratio = serving_g / (food_data.get("serving_g") or 100.0)

    # Meal nutrients for the confirmed portion
    meal_cals = round((food_data.get("calories_kcal") or 0) * ratio, 1)
    meal_protein = round((food_data.get("protein_g") or 0) * ratio, 1)
    meal_carbs = round((food_data.get("carbs_g") or 0) * ratio, 1)
    meal_fat = round((food_data.get("fat_g") or 0) * ratio, 1)

    # Current intake
    curr_cals = round(daily_intake.get("calories", 0), 1)
    curr_protein = round(daily_intake.get("protein_g", 0), 1)
    curr_carbs = round(daily_intake.get("carbs_g", 0), 1)
    curr_fat = round(daily_intake.get("fat_g", 0), 1)

    # Daily targets
    target_cals = round(daily_targets.get("calories", 2200), 1)
    target_protein = round(daily_targets.get("protein_g", 140), 1)
    target_carbs = round(daily_targets.get("carbs_g", 250), 1)
    target_fat = round(daily_targets.get("fat_g", 65), 1)

    # Projected intake
    proj_cals = round(curr_cals + meal_cals, 1)
    proj_protein = round(curr_protein + meal_protein, 1)
    proj_carbs = round(curr_carbs + meal_carbs, 1)
    proj_fat = round(curr_fat + meal_fat, 1)

    # Remaining before meal
    rem_cals_before = round(target_cals - curr_cals, 1)
    # Remaining after meal
    rem_cals_after = round(target_cals - proj_cals, 1)

    # User context
    goal = (user_profile.get("goal") or "muscle_gain").lower()
    diet_pref = (user_profile.get("diet_preference") or user_profile.get("diet") or "non_veg").lower()
    user_allergies = [a.strip().lower() for a in (user_profile.get("allergies") or []) if isinstance(a, str)]
    food_category = (food_data.get("category") or "general").lower()
    food_name = food_data.get("food_name", "Meal")
    components = food_data.get("components") or []

    warnings = []

    # 1. Dietary Restriction Checks (e.g. Vegetarian/Vegan preference vs Non-Veg food)
    if diet_pref in ("veg", "vegetarian", "vegan"):
        if any(non_veg_word in food_name.lower() for non_veg_word in ["chicken", "beef", "pork", "salmon", "fish", "meat", "egg"]):
            warnings.append(f"Contains non-vegetarian ingredients, conflicting with your '{diet_pref.upper()}' dietary preference.")

    # 2. Allergy & Ingredient Safety Checks
    if user_allergies:
        for allergy in user_allergies:
            if allergy in food_name.lower() or any(allergy in c.get("name", "").lower() for c in components):
                warnings.append(f"May contain '{allergy}', matching your recorded allergen list.")

    # Unknown / unverified ingredients warning
    if not components or food_category == "packaged_product":
        warnings.append("Ingredients could not be fully verified for allergen safety. Please check product packaging if you have severe food allergies.")

    # 3. Recommendation Logic Evaluation
    recommendation_label = "GOOD FIT"
    badge_color = "#059669" # Emerald green
    explanation = ""
    suggested_portion_g = None

    has_custom_target = bool(daily_targets.get("calories"))

    # Check for severe dietary conflict
    if warnings and any("conflicting" in w or "matching" in w for w in warnings):
        recommendation_label = "LESS SUITABLE RIGHT NOW"
        badge_color = "#DC2626" # Rose red
        explanation = f"This item conflicts with your stated {diet_pref.replace('_', '-').upper()} dietary preference or allergy profile."
    # Calorie Budget Evaluation
    elif proj_cals > target_cals + 250 or rem_cals_before < meal_cals:
        # Exceeds remaining budget
        recommendation_label = "FITS WITH ADJUSTMENTS"
        badge_color = "#D97706" # Amber orange
        
        # Calculate portion adjustment that would fit remaining cals
        if rem_cals_before > 100:
            suggested_g = round((rem_cals_before / (food_data.get("calories_kcal") or 100)) * (food_data.get("serving_g") or 100))
            suggested_portion_g = max(30, min(suggested_g, int(serving_g)))
            explanation = f"Your remaining calorie budget today is {int(rem_cals_before)} kcal. Reducing portion from {int(serving_g)}g to {suggested_portion_g}g fits your remaining target comfortably."
        else:
            explanation = f"You are close to your daily target ({int(curr_cals)} / {int(target_cals)} kcal). A smaller snack portion will help maintain your calorie balance."

    elif goal == "muscle_gain" and meal_protein >= 20:
        recommendation_label = "GOOD FIT"
        badge_color = "#059669"
        explanation = f"Excellent protein density ({meal_protein}g protein) to support muscle recovery and synthesis for your muscle gain goal."

    elif goal == "weight_loss" and meal_cals <= rem_cals_before and (meal_protein >= 15 or meal_cals <= 350):
        recommendation_label = "GOOD FIT"
        badge_color = "#059669"
        explanation = f"Fits your fat loss target nicely with a manageable calorie impact ({int(meal_cals)} kcal) and high satiety value."

    else:
        recommendation_label = "GOOD FIT"
        badge_color = "#059669"
        explanation = f"Fits comfortably within your remaining daily calorie budget ({int(rem_cals_after)} kcal left after eating)."

    if not has_custom_target:
        explanation += " (Note: Calculating exact remaining targets requires setting up your daily calorie goal in settings)."

    impact_preview = {
        "calories": {
            "current": curr_cals,
            "meal": meal_cals,
            "projected": proj_cals,
            "target": target_cals,
            "remaining_after": rem_cals_after
        },
        "protein": {
            "current_g": curr_protein,
            "meal_g": meal_protein,
            "projected_g": proj_protein,
            "target_g": target_protein
        },
        "carbs": {
            "current_g": curr_carbs,
            "meal_g": meal_carbs,
            "projected_g": proj_carbs,
            "target_g": target_carbs
        },
        "fat": {
            "current_g": curr_fat,
            "meal_g": meal_fat,
            "projected_g": proj_fat,
            "target_g": target_fat
        }
    }

    return {
        "recommendation_label": recommendation_label,
        "badge_color": badge_color,
        "explanation": explanation,
        "suggested_portion_g": suggested_portion_g,
        "warnings": warnings,
        "impact_preview": impact_preview
    }

