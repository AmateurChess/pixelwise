import os
from fastapi import FastAPI, Header, HTTPException, Request, Depends
from pydantic import BaseModel
import numpy as np
from app.classifier import (
    classify_batch,
    swap_model,
    is_hotswap_enabled_polling,
    is_hotswap_enabled_inmemory,
    set_hotswap_enabled,
)
from app.models import Prediction, SessionLocal
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from dotenv import load_dotenv

load_dotenv()

FLAG_METHOD = os.getenv("FLAG_METHOD", "inmemory").lower()


class ClassifyRequest(BaseModel):
    pixels: list[list[int]]


class ClassifyResponse(BaseModel):
    prediction: str
    confidence: float
    scores: dict[str, float]


class SwapRequest(BaseModel):
    model_path: str


class ToggleRequest(BaseModel):
    enabled: bool


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("SECRET_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")


def hotswap_currently_enabled() -> bool:
    """Fragt je nach FLAG_METHOD die passende Feature-Flag-Implementierung
    ab. Beide Methoden steuern dieselbe Funktionalitaet (swap_model), nur
    die Art, wie der Flag-Zustand gelesen wird, unterscheidet sich."""
    if FLAG_METHOD == "polling":
        return is_hotswap_enabled_polling()
    return is_hotswap_enabled_inmemory()


limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.add_middleware(SlowAPIMiddleware)
app.state.limiter = limiter


@app.on_event("startup")
def startup_event():
    try:
        swap_model(os.getenv("MODEL_PATH"))
    except Exception as e:
        print(f"Warnung: Start-Modell konnte nicht geladen werden: {e}")


@app.get("/health")
def health():
    return {"status": "ok", "model_version": "v1"}


@app.get("/results")
def results():
    db = SessionLocal()
    rows = (db.query(Prediction)
            .order_by(Prediction.created_at.desc())
            .limit(20).all())
    db.close()
    return {"results": [
        {"id": r.id,
         "prediction": r.prediction,
         "confidence": r.confidence,
         "model_version": r.model_version,
         "created_at": r.created_at.isoformat()}
        for r in rows]}


@app.post("/classify", response_model=ClassifyResponse)
@limiter.limit("30/minutes")
def classify(request: Request, req: ClassifyRequest):
    arr = np.array(req.pixels, dtype=np.uint8)[np.newaxis]
    result = classify_batch(arr)[0]
    db = SessionLocal()
    db.add(Prediction(
        prediction=result["prediction"],
        confidence=result["confidence"],
        model_version="v1"))
    db.commit()
    db.close()
    return result


@app.post("/admin/swap-model", dependencies=[Depends(verify_api_key)])
def admin_swap_model(req: SwapRequest):
    if not hotswap_currently_enabled():
        raise HTTPException(
            status_code=403,
            detail="Hotswap ist aktuell ueber das Feature Flag deaktiviert.")
    try:
        swap_model(req.model_path)
        return {"status": "ok", "model_path": req.model_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/toggle-hotswap", dependencies=[Depends(verify_api_key)])
def admin_toggle_hotswap(req: ToggleRequest):
    """Feature Flag Methode 2 (In-Memory + Lock). Setzt den Flag-Zustand
    sofort und ohne Neustart. Nur wirksam, wenn FLAG_METHOD=inmemory."""
    set_hotswap_enabled(req.enabled)
    return {"status": "ok", "hotswap_enabled": req.enabled,
            "flag_method": FLAG_METHOD}


@app.get("/admin/hotswap-status", dependencies=[Depends(verify_api_key)])
def admin_hotswap_status():
    return {"hotswap_enabled": hotswap_currently_enabled(),
            "flag_method": FLAG_METHOD}
