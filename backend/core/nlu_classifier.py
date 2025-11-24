# backend/core/nlu_classifier.py
"""
NLU classifier (offline, no external LLMs)
- TF-IDF (1-2 grams) + Logistic Regression
- Normalization: lowercase, english stopwords
- Saves model to backend/models/nlu_pipeline.joblib
- Saves label map to backend/models/nlu_labels.json
"""

import os
import json
from typing import List, Tuple, Optional, Dict, Any
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # backend/
MODEL_DIR = os.path.join(ROOT, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_FILE = os.path.join(MODEL_DIR, "nlu_pipeline.joblib")
LABEL_FILE = os.path.join(MODEL_DIR, "nlu_labels.json")

# Default label set used by train script (expandable)
DEFAULT_LABELS = [
    "expense_recording",
    "income_recording",
    "saving_recording",
    "spending_query",
    "product_frequency_query",
    "product_price_query",
    "top_expenses_query",
    "recent_transactions_query",
    "category_list_query",
    "analysis_query",
    "help",
    "unknown"
]


def build_pipeline(max_features: int = 8000, ngram_range=(1, 2), max_iter: int = 2000) -> Pipeline:
    """
    Build and return a tfidf + logistic regression pipeline.
    """
    vec = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=ngram_range, max_features=max_features)
    clf = LogisticRegression(max_iter=max_iter, C=1.0, solver="lbfgs", multi_class="auto")
    pipeline = Pipeline([("tfidf", vec), ("clf", clf)])
    return pipeline


def train_and_save(examples: List[Tuple[str, str]], model_file: str = MODEL_FILE, label_file: str = LABEL_FILE) -> None:
    """
    Train pipeline on examples and save model + labels.
    examples: list of (text, label)
    """
    if not examples:
        raise ValueError("No training examples provided")

    texts = [t for t, _ in examples]
    labels = [l for _, l in examples]

    p = build_pipeline()
    p.fit(texts, labels)

    joblib.dump(p, model_file)

    # save label ordering (pipeline.classes_)
    labels_sorted = list(p.classes_)
    with open(label_file, "w", encoding="utf-8") as f:
        json.dump(labels_sorted, f, ensure_ascii=False, indent=2)

    print(f"[NLU] Saved pipeline -> {model_file}")
    print(f"[NLU] Saved labels -> {label_file}")


def load_pipeline(model_file: str = MODEL_FILE) -> Optional[Pipeline]:
    """
    Load and return the trained pipeline, or None if not present.
    """
    if os.path.exists(model_file):
        try:
            return joblib.load(model_file)
        except Exception as e:
            print(f"[NLU] Failed to load pipeline: {e}")
            return None
    return None


def predict_intent(text: str, pipeline: Optional[Pipeline] = None) -> Dict[str, Any]:
    """
    Predict intent label and confidence.
    Returns: {"intent": label, "confidence": 0.0}
    """
    text = (text or "").strip()
    if not text:
        return {"intent": "unknown", "confidence": 0.0}

    if pipeline is None:
        pipeline = load_pipeline()
        if pipeline is None:
            return {"intent": "unknown", "confidence": 0.0}

    try:
        probs = pipeline.predict_proba([text])[0]
        labels = pipeline.classes_
        idx = int(probs.argmax())
        return {"intent": labels[idx], "confidence": float(probs[idx])}
    except Exception as e:
        print(f"[NLU] predict error: {e}")
        return {"intent": "unknown", "confidence": 0.0}
