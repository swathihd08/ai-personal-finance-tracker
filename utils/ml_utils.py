from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier

ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "dataset" / "transactions_dataset.csv"
MODEL_DIR = ROOT_DIR / "models"
MODEL_PATH = MODEL_DIR / "best_model.joblib"
ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"
METRICS_PATH = MODEL_DIR / "metrics.json"


def clean_text(text: str) -> str:
    cleaned = text.lower()
    cleaned = "".join(ch for ch in cleaned if ch.isalnum() or ch.isspace())
    return cleaned


def _should_stratify(y: pd.Series, test_size: float) -> bool:
    counts = y.value_counts()
    if counts.min() < 2:
        return False
    n_samples = len(y)
    n_classes = counts.size
    return test_size * n_samples >= n_classes and (1 - test_size) * n_samples >= n_classes


def _train_models() -> dict:
    df = pd.read_csv(DATASET_PATH)
    df = df.dropna(subset=["description", "category"])
    df["description"] = df["description"].apply(clean_text)
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df["category"])
    stratify = y if _should_stratify(pd.Series(y), test_size=0.2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        df["description"], y, test_size=0.2, random_state=42, stratify=stratify
    )

    models = {
        "Logistic Regression": Pipeline([
            ("tfidf", TfidfVectorizer(stop_words="english", ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=3000, random_state=42)),
        ]),
        "Naive Bayes": Pipeline([
            ("tfidf", TfidfVectorizer(stop_words="english", ngram_range=(1, 2))),
            ("clf", MultinomialNB()),
        ]),
        "Random Forest": Pipeline([
            ("tfidf", TfidfVectorizer(stop_words="english", ngram_range=(1, 2))),
            ("clf", RandomForestClassifier(n_estimators=150, random_state=42)),
        ]),
    }

    results = {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)
        results[name] = {
            "model": model,
            "accuracy": accuracy_score(y_test, predictions),
            "precision": precision_score(y_test, predictions, average="weighted", zero_division=0),
            "recall": recall_score(y_test, predictions, average="weighted", zero_division=0),
            "f1": f1_score(y_test, predictions, average="weighted", zero_division=0),
            # Build a full confusion matrix that includes all label encoder classes
            "confusion_matrix": confusion_matrix(y_test, predictions, labels=np.arange(len(label_encoder.classes_))).tolist(),
            "labels": label_encoder.classes_.tolist(),
        }

    best_name = max(results, key=lambda name: results[name]["f1"])
    best_result = results[best_name]
    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(best_result["model"], MODEL_PATH)
    joblib.dump(label_encoder, ENCODER_PATH)
    return {"best_model": best_name, **best_result}


def ensure_model_ready() -> dict:
    MODEL_DIR.mkdir(exist_ok=True)
    if not MODEL_PATH.exists() or not ENCODER_PATH.exists():
        return _train_models()
    return {"best_model": MODEL_PATH.name, "model": joblib.load(MODEL_PATH), "label_encoder": joblib.load(ENCODER_PATH)}


def predict_category(description: str) -> str:
    model_info = ensure_model_ready()
    model = model_info["model"]
    label_encoder = model_info["label_encoder"]
    prediction = model.predict([clean_text(description)])[0]
    return label_encoder.inverse_transform([prediction])[0]


def get_model_metrics() -> dict:
    if not MODEL_PATH.exists() or not ENCODER_PATH.exists():
        ensure_model_ready()
    model = joblib.load(MODEL_PATH)
    label_encoder = joblib.load(ENCODER_PATH)
    df = pd.read_csv(DATASET_PATH)
    df = df.dropna(subset=["description", "category"])
    df["description"] = df["description"].apply(clean_text)
    y = label_encoder.transform(df["category"])
    # Use stratify only when safe for the dataset size
    stratify = y if _should_stratify(pd.Series(y), test_size=0.2) else None
    X_train, X_test, y_train, y_test = train_test_split(
        df["description"], y, test_size=0.2, random_state=42, stratify=stratify
    )
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)
    return {
        "accuracy": accuracy_score(y_test, predictions),
        "precision": precision_score(y_test, predictions, average="weighted", zero_division=0),
        "recall": recall_score(y_test, predictions, average="weighted", zero_division=0),
        "f1": f1_score(y_test, predictions, average="weighted", zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predictions, labels=np.arange(len(label_encoder.classes_))).tolist(),
        "labels": label_encoder.classes_.tolist(),
    }
