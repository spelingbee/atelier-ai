"""
AtelierAI — FastAPI app (NEW FILE, additive). Тонкая обёртка над service.py.

Запуск:  uvicorn api:app --reload --port 8000
Зависимости: fastapi, uvicorn, python-multipart, pydantic (см. requirements.txt)
Переменные окружения:
    ANTHROPIC_API_KEY   — если нет, классификатор работает в mock-режиме
    STORAGE_BACKEND     — local|s3 (дефолт local)
"""
from __future__ import annotations

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import db
import service

app = FastAPI(title="AtelierAI — Skirt Pattern API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup():
    service.ensure_db()
    # раздаём локальное хранилище как /files (только для LocalStorage / MVP)
    try:
        app.mount("/files", StaticFiles(directory="/data/skirt/storage"), name="files")
    except Exception:
        pass


class MeasurementsIn(BaseModel):
    session_id: str
    waist_cm: float = Field(..., ge=50, le=200)
    hip_cm: float = Field(..., ge=60, le=220)
    length_cm: float = Field(..., ge=30, le=150)
    ease_waist: float = Field(1.0, ge=0, le=8)
    ease_hip: float = Field(4.0, ge=0, le=12)
    seam_allowance: float = Field(1.5, ge=0.5, le=3.0)
    skirt_type_override: str | None = None
    waistband: str | None = None
    closure: str | None = None
    overlay: str | None = None
    pocket_type: str | None = None

    @field_validator("hip_cm")
    @classmethod
    def hip_ge_waist(cls, v, info):
        w = info.data.get("waist_cm")
        if w is not None and v < w:
            raise ValueError("Обхват бёдер должен быть ≥ обхвата талии")
        return v


@app.post("/api/v1/sessions")
def create_session():
    return {"session_id": db.create_session()}


@app.post("/api/v1/analyze")
async def analyze(session_id: str = Form(...), file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Только JPEG, PNG, WebP")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Файл > 10 МБ")
    res = await service.analyze(session_id, content, file.filename or "upload.jpg")
    return {
        "session_id": res.session_id, "analysis_id": res.analysis_id,
        "skirt_type": res.skirt_type, "confidence": res.confidence,
        "length_hint_cm": res.length_hint_cm, "ai_params": res.ai,
        "message": f"Тип: {res.skirt_type} (уверенность {res.confidence:.0%})",
    }


@app.post("/api/v1/generate")
def generate(data: MeasurementsIn):
    try:
        res = service.generate(
            data.session_id, data.waist_cm, data.hip_cm, data.length_cm,
            data.ease_waist, data.ease_hip, data.seam_allowance,
            data.skirt_type_override,
            waistband=data.waistband,
            closure=data.closure,
            overlay=data.overlay,
            pocket_type=data.pocket_type)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return res.__dict__


@app.get("/api/v1/export/{job_id}")
def export(job_id: str, format: str = "pdf"):
    try:
        return service.export_links(job_id, format)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.get("/health")
def health():
    return {"status": "ok"}
