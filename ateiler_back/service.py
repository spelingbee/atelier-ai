"""
AtelierAI — Service layer (NEW FILE, additive).

Оркестрация БЕЗ привязки к веб-фреймворку — это позволяет тестировать весь
пайплайн (analyze -> generate -> export) без FastAPI/сети.

Импортирует существующий движок (patterns.py, export.py) БЕЗ изменений.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from dataclasses import dataclass, asdict, field
from typing import Dict, Optional

import db
from storage import get_storage
from ai_classifier import classify_skirt_image
from patterns import Measurements, build_pattern
from export import export_svg, export_pdf_tiled

_storage = get_storage()


@dataclass
class AnalyzeResult:
    session_id: str
    analysis_id: str
    skirt_type: str
    confidence: float
    length_hint_cm: int
    ai: Dict


@dataclass
class GenerateResult:
    job_id: str
    session_id: str
    skirt_type: str
    pieces: list
    svg_url: str
    pdf_url: str
    pages_a4: str
    sewing_notes: list = field(default_factory=list)


def ensure_db():
    db.init_db()


async def analyze(session_id: str, image_bytes: bytes, filename: str, provider: Optional[str] = None) -> AnalyzeResult:
    """Сохранить изображение, вызвать классификатор, сохранить результат."""
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    image_key = f"uploads/{session_id}/{uuid.uuid4().hex}{ext}"
    _storage.put_bytes(image_key, image_bytes)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(image_bytes)
        tmp_path = tmp.name
    try:
        ai = await classify_skirt_image(tmp_path, provider=provider)
    finally:
        os.unlink(tmp_path)

    analysis_id = db.save_analysis(session_id, image_key, ai)
    return AnalyzeResult(
        session_id=session_id, analysis_id=analysis_id,
        skirt_type=ai["skirt_type"], confidence=ai["confidence"],
        length_hint_cm=ai["length_hint_cm"], ai=ai)


def generate(session_id: str, waist_cm: float, hip_cm: float, length_cm: float,
             ease_waist: float = 1.0, ease_hip: float = 4.0,
             seam_allowance: float = 1.5,
             skirt_type_override: Optional[str] = None,
             waistband: Optional[str] = None,
             closure: Optional[str] = None,
             overlay: Optional[str] = None,
             pocket_type: Optional[str] = None) -> GenerateResult:
    """Взять тип из последнего анализа (или override), построить лекало, экспортировать."""
    analysis = db.get_latest_analysis(session_id)
    if not analysis and not skirt_type_override:
        raise ValueError("Сначала загрузите изображение (analyze)")
    skirt_type = skirt_type_override or analysis["skirt_type"]
    analysis_id = analysis["id"] if analysis else None

    m = Measurements(waist_cm=waist_cm, hip_cm=hip_cm, length_cm=length_cm,
                     ease_waist=ease_waist, ease_hip=ease_hip,
                     seam_allowance=seam_allowance)
    import overlays
    import reconcile
    
    details = []
    if pocket_type and pocket_type != "none":
        details.append(f"pockets:{pocket_type}")
        if pocket_type == "jeans":
            details.extend(["back_yoke", "straps"])
            
    selection = {
        "silhouette": skirt_type,
        "waistband": waistband or "band",
        "closure": closure or "zip_side",
        "overlay": overlay or "none",
        "detail": details
    }
    la = overlays.assemble(selection, m)
    pieces = la.pieces
    piece_names = [p.name for p in pieces]

    tz = reconcile.build_tech_spec(selection, m)
    sewing_notes = list(tz["construction_order"])
    if tz.get("warnings"):
        sewing_notes += [f"Предупреждение: {w}" for w in tz["warnings"]]

    job_id = uuid.uuid4().hex
    tmp_dir = tempfile.gettempdir()
    svg_local = os.path.join(tmp_dir, f"{job_id}.svg")
    pdf_local = os.path.join(tmp_dir, f"{job_id}.pdf")
    export_svg(pieces, svg_local, seam_cm=seam_allowance)
    rows, cols = export_pdf_tiled(pieces, pdf_local, seam_cm=seam_allowance)

    svg_key = f"patterns/{session_id}/{job_id}.svg"
    pdf_key = f"patterns/{session_id}/{job_id}.pdf" if os.path.exists(pdf_local) else ""
    _storage.put_file(svg_key, svg_local)
    if pdf_key:
        _storage.put_file(pdf_key, pdf_local)
        try:
            os.unlink(pdf_local)
        except OSError:
            pass

    try:
        os.unlink(svg_local)
    except OSError:
        pass

    db.save_job(session_id, analysis_id,
                {"waist_cm": waist_cm, "hip_cm": hip_cm, "length_cm": length_cm,
                 "ease_waist": ease_waist, "ease_hip": ease_hip,
                 "seam_allowance": seam_allowance},
                skirt_type, svg_key, pdf_key, piece_names, job_id=job_id)

    return GenerateResult(
        job_id=job_id, session_id=session_id, skirt_type=skirt_type,
        pieces=piece_names,
        svg_url=_storage.url(svg_key),
        pdf_url=_storage.url(pdf_key) if pdf_key else "",
        pages_a4=f"{rows}x{cols}",
        sewing_notes=sewing_notes)


def export_links(job_id: str, fmt: str = "pdf") -> Dict:
    job = db.get_job(job_id)
    if not job:
        raise ValueError("Задача не найдена")
    key = job["pdf_key"] if fmt == "pdf" else job["svg_key"]
    return {"download_url": _storage.url(key, expires=600), "expires_in": 600,
            "format": fmt, "job_id": job_id}
