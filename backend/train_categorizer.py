# ==============================================================
# TRAINING SCRIPT FOR spending_patterns_cleaned.csv (MATCHED TO YOUR DATASET)
# ==============================================================

import pandas as pd
import pickle
import json
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score

DATA_PATH = "spending_patterns_cleaned.csv"  # <-- adjust path if needed
MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

# ==============================================================
# STEP 1 — LOAD CSV
# ==============================================================

df = pd.read_csv(DATA_PATH)
print("Loaded dataset:", df.shape)

# ==============================================================
# STEP 2 — CREATE TEXT FEATURE (MATCHING YOUR COLAB FORMAT)
# ==============================================================

df["text"] = (
    df["item"].astype(str) + " " +
    df["location"].astype(str) + " " +
    df["payment_method"].astype(str)
).astype(str)

# ==============================================================
# STEP 3 — ENCODE TARGET LABELS
# ==============================================================

le = LabelEncoder()
df["label"] = le.fit_transform(df["category_clean"])

label_map = {cls: int(code) for cls, code in zip(le.classes_, le.transform(le.classes_))}

with open(os.path.join(MODEL_DIR, "label_mapping.json"), "w") as f:
    json.dump(label_map, f, indent=2)

print("Label mapping saved.")

# ==============================================================
# STEP 4 — TRAIN/TEST SPLIT
# ==============================================================

X = df["text"]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ==============================================================
# STEP 5 — TF-IDF VECTORIZER
# ==============================================================

vectorizer = TfidfVectorizer(
    max_features=4000,
    ngram_range=(1, 2),
    min_df=3
)

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

with open(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"), "wb") as f:
    pickle.dump(vectorizer, f)

print("Vectorizer saved.")

# ==============================================================
# STEP 6 — TRAIN LOGISTIC REGRESSION
# ==============================================================

model = LogisticRegression(
    max_iter=2000,
    C=2.0,
    solver="lbfgs",
    class_weight="balanced",
    n_jobs=-1
)

model.fit(X_train_vec, y_train)

with open(os.path.join(MODEL_DIR, "logistic_model.pkl"), "wb") as f:
    pickle.dump(model, f)

print("Model saved.")

# ==============================================================
# STEP 7 — EVALUATION
# ==============================================================

y_pred = model.predict(X_test_vec)

print("\nClassification Report:\n")
print(classification_report(y_test, y_pred, target_names=le.classes_))

macro_f1 = f1_score(y_test, y_pred, average="macro")
print("Macro F1:", macro_f1)
