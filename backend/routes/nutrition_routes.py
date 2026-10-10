import base64
import re
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from core.food_vision import analyze_food_image_bytes, PACKAGED_AND_FRESH_NUTRITION_DB, query_openfoodfacts_api
from core.diet_advisor import evaluate_diet_recommendation

router = APIRouter(prefix="/api/nutrition", tags=["nutrition_scanner"])

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

class FoodScanRequest(BaseModel):
    user_id: Optional[str] = "guest"
    image: str = Field(..., description="Base64 encoded image string (JPEG, PNG, or WebP)")
    meal_type: Optional[str] = Field("snack", description="breakfast, lunch, dinner, or snack")
    user_description: Optional[str] = Field(None, description="Optional user note or portion hint")

class PortionRecalculateRequest(BaseModel):
    serving_g: float = Field(..., gt=0)
    base_100g_data: Dict[str, Any]

class RecommendationEvaluateRequest(BaseModel):
    food_data: Dict[str, Any]
    serving_g: float = Field(..., gt=0)
    user_profile: Optional[Dict[str, Any]] = {}
    daily_intake: Optional[Dict[str, Any]] = {}
    daily_targets: Optional[Dict[str, Any]] = {}

def validate_and_decode_image(base64_str: str) -> Dict[str, Any]:
    """
    Validates base64 image data:
    1. Checks for non-empty string.
    2. Strips data URL prefix if present.
    3. Validates base64 decoding.
    4. Inspects binary magic header bytes to verify JPEG, PNG, or WebP format.
    5. Enforces 10MB binary size limit.
    """
    if not base64_str or not isinstance(base64_str, str):
        return {"valid": False, "bytes": None, "mime": None, "error": "Image data is required."}

    data_uri_match = re.match(r"^data:(image\/(jpeg|png|webp));base64,", base64_str)
    header_mime = data_uri_match.group(1) if data_uri_match else None

    clean_base64 = re.sub(r"^data:image\/[a-zA-Z]+;base64,", "", base64_str).strip()
    if not clean_base64:
        return {"valid": False, "bytes": None, "mime": None, "error": "Empty image payload after prefix stripping."}

    try:
        image_bytes = base64.b64decode(clean_base64, validate=True)
    except Exception as decode_err:
        return {"valid": False, "bytes": None, "mime": None, "error": f"Invalid base64 encoding: {decode_err}"}

    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        return {
            "valid": False,
            "bytes": None,
            "mime": None,
            "error": f"Image size ({round(len(image_bytes)/(1024*1024), 2)}MB) exceeds the 10MB maximum limit."
        }

    detected_mime = None
    if image_bytes.startswith(b"\xff\xd8"):
        detected_mime = "image/jpeg"
    elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        detected_mime = "image/png"
    elif image_bytes.startswith(b"RIFF") and len(image_bytes) >= 12 and image_bytes[8:12] == b"WEBP":
        detected_mime = "image/webp"

    if not detected_mime:
        return {
            "valid": False,
            "bytes": None,
            "mime": None,
            "error": "File binary header does not match supported image formats (JPEG, PNG, WebP)."
        }

    return {
        "valid": True,
        "bytes": image_bytes,
        "mime": detected_mime,
        "clean_base64": clean_base64,
        "error": None
    }


@router.post("/validate-image")
def validate_food_image_endpoint(req: FoodScanRequest):
    result = validate_and_decode_image(req.image)

    if not result["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "status": "rejected",
                "reason": result["error"],
                "message": "Invalid or unreadable image upload."
            }
        )

    return {
        "status": "valid",
        "mime_type": result["mime"],
        "size_bytes": len(result["bytes"]),
        "size_mb": round(len(result["bytes"]) / (1024 * 1024), 2),
        "message": "Image passed server-side format, binary header, and size validation."
    }


@router.post("/scan-food")
def scan_and_identify_food(req: FoodScanRequest):
    validation = validate_and_decode_image(req.image)
    if not validation["valid"]:
        return {
            "outcome": "C",
            "is_food": False,
            "confidence": 0.0,
            "message": "This image doesn't appear to contain a recognisable food item. Please take another photo or upload a clear picture of your meal.",
            "food_data": None
        }

    analysis = analyze_food_image_bytes(
        image_bytes=validation["bytes"],
        mime_type=validation.get("mime") or "image/jpeg",
        clean_base64=validation.get("clean_base64"),
        user_description=req.user_description
    )

    return analysis


@router.post("/recalculate")
def recalculate_portion_nutrition(req: PortionRecalculateRequest):
    ratio = req.serving_g / 100.0
    base = req.base_100g_data

    return {
        "serving_g": req.serving_g,
        "calories_kcal": round(base.get("calories_kcal", 0) * ratio, 1),
        "protein_g": round(base.get("protein_g", 0) * ratio, 1),
        "carbs_g": round(base.get("carbs_g", 0) * ratio, 1),
        "fat_g": round(base.get("fat_g", 0) * ratio, 1),
        "sat_fat_g": round(base.get("sat_fat_g", 0) * ratio, 1),
        "sugar_g": round(base.get("sugar_g", 0) * ratio, 1),
        "fiber_g": round(base.get("fiber_g", 0) * ratio, 1),
        "sodium_mg": round(base.get("sodium_mg", 0) * ratio, 1),
    }


@router.post("/evaluate-recommendation")
def evaluate_recommendation_endpoint(req: RecommendationEvaluateRequest):
    """
    AI Diet Advisor Endpoint: Evaluates how well a scanned meal fits the user's
    biometrics, fitness goals, daily targets, and current recorded intake.
    Returns: GOOD FIT / FITS WITH ADJUSTMENTS / LESS SUITABLE RIGHT NOW + Plain-language explanation + Impact preview.
    """
    return evaluate_diet_recommendation(
        food_data=req.food_data,
        serving_g=req.serving_g,
        user_profile=req.user_profile or {},
        daily_intake=req.daily_intake or {},
        daily_targets=req.daily_targets or {}
    )
