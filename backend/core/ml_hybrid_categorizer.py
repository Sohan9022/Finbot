import os
import json
import pickle
from typing import Dict, Any, List, Tuple

from core.category_learner import HybridCategoryLearner

MODEL_DIR = "models"
VECTORIZER_PATH = os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl")
MODEL_PATH = os.path.join(MODEL_DIR, "logistic_model.pkl")
LABEL_PATH = os.path.join(MODEL_DIR, "label_mapping.json")


class MLHybridCategorizer:

    def __init__(self, user_id: int, ml_weight: float = 0.65):
        """
        ml_weight: float (0–1)
            0.65 = 65% ML + 35% Hybrid (recommended)
        """
        self.user_id = int(user_id)
        self.ml_weight = ml_weight

        # Load Hybrid learner
        self.hybrid = HybridCategoryLearner(user_id)

        # Load ML model + vectorizer + label mapping
        if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
            with open(VECTORIZER_PATH, "rb") as f:
                self.vectorizer = pickle.load(f)

            with open(MODEL_PATH, "rb") as f:
                self.model = pickle.load(f)

            with open(LABEL_PATH, "r") as f:
                label_map = json.load(f)

            # Reverse to convert prediction integer → category string
            self.id_to_label = {v: k for k, v in label_map.items()}
        else:
            self.vectorizer = None
            self.model = None
            self.id_to_label = {}

    # ------------------------------------------------------------
    # INTERNAL — ML prediction
    # ------------------------------------------------------------
    def _ml_predict(self, text: str, top_k: int = 3) -> List[Tuple[str, float]]:
        if not self.vectorizer or not self.model:
            return []

        vec = self.vectorizer.transform([text])
        probs = self.model.predict_proba(vec)[0]

        # Get top classes
        sorted_idx = probs.argsort()[::-1][:top_k]

        results = []
        for idx in sorted_idx:
            label = self.id_to_label.get(idx)
            prob = float(probs[idx])
            results.append((label, prob))

        return results

    # ------------------------------------------------------------
    # MAIN CATEGORY SUGGESTION METHOD
    # ------------------------------------------------------------
    def suggest(self, item: str, location: str, payment_method: str) -> Dict[str, Any]:
        """
        Combine ML + Hybrid predictions.

        item + location + payment_method → same text used in training.
        """

        # Create ML text feature (MATCHING YOUR TRAINING FORMAT)
        composed = f"{item} {location} {payment_method}".strip()

        # ML prediction
        ml_preds = self._ml_predict(composed)

        # Hybrid prediction (0–100 scores → convert to 0–1)
        hybrid_preds_raw = self.hybrid.suggest_category(
            text=composed,
            merchant=None,  # your dataset does not use merchant
            amount=None     # your dataset does not use amount
        )

        hybrid_preds = [(cat, score / 100.0) for cat, score in hybrid_preds_raw]

        # Score combining
        final_scores = {}

        # Add ML weighted scores
        for cat, prob in ml_preds:
            final_scores[cat] = final_scores.get(cat, 0) + prob * self.ml_weight

        # Add Hybrid weighted scores
        for cat, score in hybrid_preds:
            final_scores[cat] = final_scores.get(cat, 0) + score * (1 - self.ml_weight)

        if not final_scores:
            return {
                "final_category": None,
                "scores": {},
                "ml": ml_preds,
                "hybrid": hybrid_preds_raw
            }

        # Sort by score descending
        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        final_category, final_score = ranked[0]

        # Return full structured output
        return {
            "final_category": final_category,
            "final_score": float(final_score),
            "scores": {cat: float(score) for cat, score in ranked},
            "ml_predictions": ml_preds,
            "hybrid_predictions": hybrid_preds_raw,
            "composed_text": composed
        }
