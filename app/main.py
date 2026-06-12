import os
from fastapi import FastAPI, Header, HTTPException, Request, Depends
from pydantic import BaseModel
import numpy as np
from app.classifier import classify_batch, swap_model
from app.models import Prediction, SessionLocal
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

ENABLE_HOTSWAP = os.getenv("ENABLE_HOTSWAP", "false").lower() == "true"

class ClassifyRequest(BaseModel):
    pixels: list[list[int]]

class ClassifyResponse(BaseModel):
    prediction: str
    confidence: float
    scores: dict[str, float]

class SwapRequest(BaseModel):
    model_path: str

def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != os.getenv("SECRET_API_KEY"):
        raise HTTPException(
            status_code=401, detail="Invalid API key")

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()

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

@app.post("/classify",
        response_model=ClassifyResponse,
        dependencies=[Depends(verify_api_key)])
@limiter.limit("30/minutes")
def classify(request: Request, req: ClassifyRequest):
    arr = np.array(req.pixels,
                   dtype=np.uint8)[np.newaxis]
    result = classify_batch(arr)[0]
    db = SessionLocal()
    db.add(Prediction(
        prediction=result["prediction"],
        confidence=result["confidence"],
        model_version="v1"))
    db.commit()
    db.close()
    return result

@app.post("/admin/swap-model",
          dependencies=[Depends(verify_api_key)])
def admin_swap_model(req: SwapRequest):
    if not ENABLE_HOTSWAP:
        raise HTTPException(
            status_code=403,
            detail="Hotswap ist in dieser Methode deaktiviert.")
    try:
        swap_model(req.model_path)
        return {"status": "ok", "model_path": req.model_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
