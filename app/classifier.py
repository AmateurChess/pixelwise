import os
import joblib
import numpy as np
from dotenv import load_dotenv
import threading
load_dotenv()
CLASSES = ["1","2","3","4","5","6","7","8","9"]
_pipeline = joblib.load(os.getenv("MODEL_PATH"))
assert list(_pipeline.classes_) == CLASSES, \
    f"Model/CLASSES mismatch: {_pipeline.classes_}"
def classify_batch(images: np.ndarray) -> list[dict]:
    if images.ndim != 3 or images.shape[1:] != (28, 28):
        raise ValueError(
           f"Expected (N,28,28), got {images.shape}")
    arr = (images > 128).astype(float).reshape(
       len(images), -1)
    probs = _pipeline.predict_proba(arr)
    return [
        {"prediction": CLASSES[p.argmax()],
        "confidence": float(p.max()),
        "scores": dict(zip(CLASSES, p.tolist()))}
        for p in probs
    ]
def classify(image: np.ndarray) -> dict:
    return classify_batch(image[np.newaxis])[0]

_pipeline = None
_lock = threading.Lock()

def get_pipeline():
    """Sicherer Zugriff auf das aktuelle Modell."""
    with _lock:
        if _pipeline is None:
            raise RuntimeError("Modell wurde noch nicht initialisiert!")
        return _pipeline

def swap_model(new_model_path: str):
    global _pipeline
    new_pipeline = joblib.load(new_model_path)
    assert list(new_pipeline.classes_) == CLASSES, "Mismatch"
    with _lock:
        _pipeline = new_pipeline

def classify_batch(data):
    pipeline = get_pipeline() 
    return pipeline.predict_proba(data)
