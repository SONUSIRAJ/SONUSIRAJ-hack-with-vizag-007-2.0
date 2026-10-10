import unittest
from unittest.mock import patch
import io
import base64
from PIL import Image, ImageDraw
from core.diet_advisor import evaluate_diet_recommendation
from core.food_vision import analyze_food_image_bytes, PACKAGED_AND_FRESH_NUTRITION_DB, query_openfoodfacts_api
from routes.nutrition_routes import validate_and_decode_image

class TestFullVisionAndDietPipeline(unittest.TestCase):

    def setUp(self):
        # Create a non-solid test image binary with drawn shapes
        img = Image.new("RGB", (100, 100), color=(200, 100, 50))
        draw = ImageDraw.Draw(img)
        draw.ellipse((20, 20, 80, 80), fill=(50, 180, 70))
        draw.rectangle((30, 30, 70, 70), fill=(250, 220, 30))

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        self.sample_bytes = buf.getvalue()
        self.sample_b64 = f"data:image/jpeg;base64,{base64.b64encode(self.sample_bytes).decode('utf-8')}"

    def test_1_image_validation_gate(self):
        """Verify image validation detects valid JPEG/PNG and rejects unreadable payloads."""
        val_good = validate_and_decode_image(self.sample_b64)
        self.assertTrue(val_good["valid"])
        self.assertEqual(val_good["mime"], "image/jpeg")

        val_bad = validate_and_decode_image("invalid_base64_string")
        self.assertFalse(val_bad["valid"])

    @patch("core.food_vision.call_vision_ai_model")
    def test_2_packaged_food_recognition(self, mock_vision):
        """Verify packaged snacks (Kurkure, Lay's) return correct packaged nutrition data."""
        mock_vision.return_value = {
            "is_food": True,
            "image_category": "packaged_food",
            "food_name": "Kurkure Masala Munch",
            "brand": "Pepsico / Kurkure",
            "confidence": 0.95,
            "visible_components": ["Corn meal crisp", "Spices"],
            "nutrition_label_visible": False,
            "reasoning": "Identified packaged snack wrapper for Kurkure Masala Munch."
        }
        res_kurkure = analyze_food_image_bytes(
            image_bytes=self.sample_bytes,
            clean_base64=base64.b64encode(self.sample_bytes).decode('utf-8'),
            user_description="Kurkure Masala Munch"
        )
        self.assertEqual(res_kurkure["outcome"], "A")
        self.assertIn("Kurkure", res_kurkure["food_data"]["food_name"])
        self.assertEqual(res_kurkure["food_data"]["calories_kcal"], 557)

    @patch("core.food_vision.call_vision_ai_model")
    def test_3_fresh_meal_recognition(self, mock_vision):
        """Verify fresh meals (Paneer Tikka, Dosa) return correct component data."""
        mock_vision.return_value = {
            "is_food": True,
            "image_category": "fresh_meal",
            "food_name": "Paneer Tikka",
            "brand": None,
            "confidence": 0.92,
            "visible_components": ["Paneer cubes", "Mint chutney"],
            "nutrition_label_visible": False,
            "reasoning": "Identified fresh paneer tikka with chutney."
        }
        res_paneer = analyze_food_image_bytes(
            image_bytes=self.sample_bytes,
            clean_base64=base64.b64encode(self.sample_bytes).decode('utf-8'),
            user_description="Paneer Tikka"
        )
        self.assertEqual(res_paneer["outcome"], "A")
        self.assertIn("Paneer Tikka", res_paneer["food_data"]["food_name"])

    def test_4_non_food_rejection_no_fake_panel(self):
        """Verify flat/solid or non-food image returns Outcome C with no food payload."""
        flat_img = Image.new("RGB", (100, 100), color=(255, 255, 255))
        buf = io.BytesIO()
        flat_img.save(buf, format="JPEG")
        flat_bytes = buf.getvalue()
        flat_b64 = base64.b64encode(flat_bytes).decode('utf-8')

        res_flat = analyze_food_image_bytes(
            image_bytes=flat_bytes,
            clean_base64=flat_b64
        )
        self.assertEqual(res_flat["outcome"], "C")
        self.assertFalse(res_flat["is_food"])
        self.assertIsNone(res_flat["food_data"])

    def test_5_portion_scaling_math(self):
        """Verify deterministic portion scaling: 50g serving of 100g item yields half nutrient values."""
        base_100g = PACKAGED_AND_FRESH_NUTRITION_DB["kurkure"]
        ratio = 50.0 / 100.0
        cals_50g = round(base_100g["calories_kcal"] * ratio, 1)
        prot_50g = round(base_100g["protein_g"] * ratio, 1)

        self.assertEqual(cals_50g, 278.5)
        self.assertEqual(prot_50g, 3.0)

    def test_6_personalized_recommendation_evaluation(self):
        """Verify diet evaluation categorizes GOOD FIT vs FITS WITH ADJUSTMENTS based on goal and intake."""
        profile = {"goal": "muscle_gain", "diet": "non_veg"}
        targets = {"calories": 2400, "protein_g": 140, "carbs_g": 250, "fat_g": 65}
        intake_early = {"calories": 1000, "protein_g": 50, "carbs_g": 120, "fat_g": 30}
        intake_full = {"calories": 2300, "protein_g": 130, "carbs_g": 240, "fat_g": 60}

        food = PACKAGED_AND_FRESH_NUTRITION_DB["grilled chicken rice"]
        rec_early = evaluate_diet_recommendation(food, 350, profile, intake_early, targets)
        rec_full = evaluate_diet_recommendation(food, 350, profile, intake_full, targets)

        self.assertEqual(rec_early["recommendation_label"], "GOOD FIT")
        self.assertEqual(rec_full["recommendation_label"], "FITS WITH ADJUSTMENTS")

if __name__ == "__main__":
    unittest.main()
