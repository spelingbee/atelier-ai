"""
AtelierAI — РАСШИРЕНИЕ API (NEW FILE, аддитивно). Не редактирует api.py.

Новые эндпоинты (APIRouter), подключаются через app_ext.py:
  POST /api/v2/analyze        — классификация любым ИИ (provider=anthropic|gemini|mock)
  POST /api/v2/analyze-both   — ОБА ИИ сразу (A/B сравнение точности)
  POST /api/v2/concept        — ИИ-концепт-картинка по фото + признакам
  GET  /api/v2/skirt-types    — список всех типов (вкл. новые)
"""

import os
import tempfile
import uuid


from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

import ai_providers
import concept as concept_mod
import skirt_types_extra  # авто-регистрация новых типов
import skirt_types_more   # авто-регистрация ещё типов (tulip/mermaid/hi_low/bubble/skort)
from patterns import PATTERN_REGISTRY

router = APIRouter()
_ALLOWED_CT = {"image/jpeg", "image/png", "image/webp"}
_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


async def _save_tmp(file: UploadFile) -> str:
    if file.content_type not in _ALLOWED_CT:
        raise HTTPException(400, "Только JPEG, PNG, WebP")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Файл > 10 МБ")
    ext = _EXT.get(file.content_type, ".jpg")
    path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}{ext}")
    with open(path, "wb") as f:
        f.write(content)
    return path


@router.get("/api/v2/skirt-types")
def skirt_types():
    return {"types": sorted(PATTERN_REGISTRY.keys()),
            "new": ["pleated", "tiered", "yoke",
                    "tulip", "mermaid", "hi_low", "bubble", "skort", "culottes", "gored_6"]}


@router.post("/api/v2/analyze")
async def analyze_v2(file: UploadFile = File(...),
                     provider: str | None = Form(None)):
    """provider: anthropic | gemini | mock | (пусто = авто по ENV/ключам)."""
    path = await _save_tmp(file)
    try:
        res = await ai_providers.classify_skirt_image(path, provider)
    finally:
        os.unlink(path)
    return res


@router.post("/api/v2/analyze-both")
async def analyze_both(file: UploadFile = File(...)):
    """Запускает ОБА ИИ и возвращает сравнение {anthropic, gemini, agree, chosen}."""
    path = await _save_tmp(file)
    try:
        return await ai_providers.classify_with_both(path)
    finally:
        os.unlink(path)


@router.post("/api/v2/concept")
async def concept_v2(files: list[UploadFile] = File(...),
                     skirt_type: str = Form("a_line"),
                     estimated_length: str = Form("midi"),
                     provider: str | None = Form(None)):
    """Концепт-картинка по 1-3 фото + признакам. Возвращает PNG."""
    paths = [await _save_tmp(f) for f in files[:3]]
    try:
        out = concept_mod.generate_concept(
            {"skirt_type": skirt_type, "estimated_length": estimated_length},
            reference_images=paths, provider=provider)
    finally:
        for p in paths:
            try:
                os.unlink(p)
            except OSError:
                pass
    return FileResponse(out["path"], media_type="image/png",
                        headers={"X-Concept-Provider": out["provider"]})
