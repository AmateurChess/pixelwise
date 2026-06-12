import os
import joblib
import numpy as np
from dotenv import load_dotenv
import threading

load_dotenv()

CLASSES = ["1","2","3","4","5","6","7","8","9"]

_pipeline = None
_lock = threading.Lock()

def swap_model(new_model_path: str):
    global _pipeline
    new_pipeline = joblib.load(new_model_path)
    assert list(new_pipeline.classes_) == CLASSES, \
        f"Model/CLASSES mismatch: {new_pipeline.classes_}"
    with _lock:
        _pipeline = new_pipeline

def get_pipeline():
    with _lock:
        if _pipeline is None:
            raise RuntimeError("Modell wurde noch nicht initialisiert!")
        return _pipeline

def classify_batch(images: np.ndarray) -> list[dict]:
    if images.ndim != 3 or images.shape[1:] != (28, 28):
        raise ValueError(
            f"Expected (N,28,28), got {images.shape}")
    arr = (images > 128).astype(float).reshape(len(images), -1)
    pipeline = get_pipeline()
    probs = pipeline.predict_proba(arr)
    return [
        {"prediction": CLASSES[p.argmax()],
         "confidence": float(p.max()),
         "scores": dict(zip(CLASSES, p.tolist()))}
        for p in probs
    ]

def classify(image: np.ndarray) -> dict:
    return classify_batch(image[np.newaxis])[0] 
