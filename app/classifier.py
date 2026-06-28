import os
import json
import time
import threading
import joblib
import numpy as np
from dotenv import load_dotenv

load_dotenv()

CLASSES = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

_pipeline = joblib.load(os.getenv("MODEL_PATH"))
assert list(_pipeline.classes_) == CLASSES, \
    f"Model/CLASSES mismatch: {_pipeline.classes_}"

_swap_lock = threading.Lock()


def swap_model(new_model_path: str) -> None:
    """Tauscht das aktive Modell zur Laufzeit aus, ohne den Prozess neu zu
    starten. Das neue Modell wird vollstaendig geladen, bevor die globale
    Variable atomar unter dem Lock ersetzt wird."""
    global _pipeline
    new_pipeline = joblib.load(new_model_path)
    assert list(new_pipeline.classes_) == CLASSES, \
        f"Model/CLASSES mismatch: {new_pipeline.classes_}"
    with _swap_lock:
        _pipeline = new_pipeline


def classify_batch(images: np.ndarray) -> list[dict]:
    if images.ndim != 3 or images.shape[1:] != (28, 28):
        raise ValueError(f"Expected (N,28,28), got {images.shape}")
    arr = (images > 128).astype(float).reshape(len(images), -1)
    with _swap_lock:
        pipeline = _pipeline
    probs = pipeline.predict_proba(arr)
    return [
        {"prediction": CLASSES[p.argmax()],
         "confidence": float(p.max()),
         "scores": dict(zip(CLASSES, p.tolist()))}
        for p in probs
    ]


def classify(image: np.ndarray) -> dict:
    return classify_batch(image[np.newaxis])[0]

FLAGS_FILE = os.getenv("FLAGS_FILE", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "flags.json"))
CHECK_INTERVAL = float(os.getenv("FLAG_POLL_INTERVAL_SECONDS", "5"))

_poll_lock = threading.Lock()
_last_check = 0.0
_polled_hotswap_enabled = False


def is_hotswap_enabled_polling() -> bool:
    """Feature-Flag-Methode 1 (Polling). Liest flags.json hoechstens einmal
    pro CHECK_INTERVAL neu ein. Aenderungen an der Datei wirken sich daher
    erst nach bis zu CHECK_INTERVAL Sekunden aus."""
    global _last_check, _polled_hotswap_enabled
    now = time.time()
    with _poll_lock:
        if now - _last_check > CHECK_INTERVAL:
            try:
                with open(FLAGS_FILE) as f:
                    data = json.load(f)
                _polled_hotswap_enabled = bool(data.get("hotswap_enabled", False))
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            _last_check = now
        return _polled_hotswap_enabled

_flag_lock = threading.Lock()
_inmemory_hotswap_enabled = False

def set_hotswap_enabled(value: bool) -> None:
    global _inmemory_hotswap_enabled
    with _flag_lock:
        _inmemory_hotswap_enabled = value

def is_hotswap_enabled_inmemory() -> bool:
    with _flag_lock:
        return _inmemory_hotswap_enabled
