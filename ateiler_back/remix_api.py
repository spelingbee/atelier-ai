"""
AtelierAI — REMIX API (NEW FILE, аддитивно). Не редактирует api.py.

Эндпоинт «собрать юбку из 2–3 референсов» (композиция признаков,
не генерация лекала нейросетью). Подключается через app_ext.py.

  POST /api/v1/remix          — мерки + признаки референсов → рецепт + SVG
  GET  /api/v1/remix/types    — что умеет remix (силуэты + детали)
"""
from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import asdict
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from patterns import Measurements, PATTERN_REGISTRY
import skirt_types_extra  # noqa: F401  регистрация
import skirt_types_more   # noqa: F401  регистрация
import remix as remix_mod
import export

router = APIRouter()


class MeasIn(BaseModel):
    waist_cm: float
    hip_cm: float
    length_cm: float = 70.0
    ease_waist: float = 1.0
    ease_hip: float = 4.0
    seam_allowance: float = 1.5


class RemixIn(BaseModel):
    measurements: MeasIn
    # каждый элемент — вывод классификатора или ручной dict признаков
    features: List[Dict]
    # какой референс (индекс) даёт какой признак: {silhouette, length, details}
    selection: Optional[Dict[str, int]] = None


@router.get("/api/v1/remix/types")
def remix_types():
    return {
        "silhouettes": sorted(PATTERN_REGISTRY.keys()),
        "composable_details": ["godets", "slit", "wrap", "waistband"],
        "note": "Ремикс компонует признаки из библиотеки шаблонов, декор — в инструкции.",
    }


@router.post("/api/v1/remix")
def remix_endpoint(body: RemixIn):
    if not body.features:
        raise HTTPException(400, "нужен хотя бы один референс")
    fvs = [remix_mod.extract_features(a) for a in body.features]
    try:
        recipe = remix_mod.remix(fvs, body.selection)
    except ValueError as e:
        raise HTTPException(400, str(e))
    m = Measurements(**body.measurements.dict())
    pieces = remix_mod.build_from_recipe(recipe, m)

    job = uuid.uuid4().hex[:8]
    svg_path = os.path.join(tempfile.gettempdir(), f"remix_{job}.svg")
    w, h = export.export_svg(pieces, svg_path)
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_xml = f.read()
    try:
        os.unlink(svg_path)
    except OSError:
        pass

    return {
        "recipe": asdict(recipe),
        "sewing_notes": remix_mod.sewing_notes(recipe),
        "pieces": [{"name": p.name, "quantity": p.quantity,
                    "cut_on_fold": p.cut_on_fold} for p in pieces],
        "layout_cm": {"width": round(w, 1), "height": round(h, 1)},
        "svg_xml": svg_xml,
    }
