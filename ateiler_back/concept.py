"""
AtelierAI — ИИ-ГЕНЕРАЦИЯ КАРТИНОК / КОНЦЕПТ-РЕНДЕР (NEW FILE, аддитивно).

По 1-3 фото-референсам + признакам → КОНЦЕПТ-КАРТИНКА. Это картинка, НЕ лекало.

ENV:
  IMAGE_PROVIDER   gemini | mock
  GOOGLE_API_KEY (или GEMINI_API_KEY)
  IMAGE_MODEL      imagen-3.0-generate-002
  IMAGE_EDIT_MODEL gemini-2.0-flash-preview-image-generation (мульти-референс)
"""
from __future__ import annotations

import base64
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

_LEN_RU = {"mini": "мини", "knee": "до колена", "midi": "миди", "maxi": "макси"}
_TYPE_RU = {
    "straight": "прямая", "pencil": "карандаш", "a_line": "А-силуэт",
    "half_circle": "полусолнце", "full_circle": "солнце",
    "pleated": "плиссе", "tiered": "ярусная", "yoke": "на кокетке со сборкой",
}


def build_concept_prompt(features: Dict) -> str:
    t = _TYPE_RU.get(features.get("skirt_type", ""), features.get("skirt_type", "юбка"))
    length = _LEN_RU.get(features.get("estimated_length", ""), "")
    extra = []
    if features.get("has_pleats"):
        extra.append("со складками")
    if features.get("has_godets"):
        extra.append("с клиньями-годе")
    if features.get("has_wrap"):
        extra.append("с запахом")
    if features.get("has_yoke"):
        extra.append("на кокетке")
    if features.get("has_pockets"):
        extra.append("с карманами")
    notes = features.get("silhouette_notes", "")
    parts = [f"женская юбка, силуэт {t}"]
    if length:
        parts.append(f"длина {length}")
    parts += extra
    if notes:
        parts.append(notes)
    body = ", ".join(parts)
    return (
        f"Фэшн-лукбук: {body}. Чистый студийный фон, фронтальный вид, одежда на манекене, "
        f"реалистичная ткань, без лица, без текста, product photography, high detail."
    )


def _resolve_provider(provider: Optional[str]) -> str:
    if provider:
        return provider.lower()
    env = os.getenv("IMAGE_PROVIDER")
    if env:
        return env.lower()
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return "mock"


def _mock_render(prompt: str, reference_images: List[str], out_path: str) -> str:
    from PIL import Image, ImageDraw, ImageFont
    W, H = 768, 1024
    canvas = Image.new("RGB", (W, H), (242, 240, 236))
    draw = ImageDraw.Draw(canvas)
    refs = [r for r in (reference_images or []) if r and Path(r).exists()]
    if refs:
        strip_h = 240
        cell = W // len(refs)
        for i, r in enumerate(refs):
            try:
                im = Image.open(r).convert("RGB")
                im.thumbnail((cell - 10, strip_h - 10))
                canvas.paste(im, (i * cell + 5, 5))
            except Exception:
                pass
        draw.line([(0, strip_h), (W, strip_h)], fill=(180, 180, 180), width=2)
    try:
        font = ImageFont.truetype("/usr/share/fonts/liberation/LiberationSans-Regular.ttf", 22)
        small = ImageFont.truetype("/usr/share/fonts/liberation/LiberationSans-Regular.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
        small = font
    draw.text((20, 270), "CONCEPT (offline mock)", fill=(40, 40, 40), font=font)
    words = prompt.split()
    line, y = "", 320
    for w in words:
        if len(line) + len(w) > 60:
            draw.text((20, y), line, fill=(70, 70, 70), font=small)
            y += 24
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        draw.text((20, y), line, fill=(70, 70, 70), font=small)
    draw.polygon([(W * 0.42, 520), (W * 0.58, 520), (W * 0.72, 960),
                  (W * 0.28, 960)], fill=(205, 200, 210), outline=(120, 120, 120))
    canvas.save(out_path, "PNG")
    return out_path


def _gemini_imagen(prompt: str, out_path: str) -> str:
    import httpx
    api_key = os.getenv("GOOGLE_API_KEY") or os.environ["GEMINI_API_KEY"]
    model = os.getenv("IMAGE_MODEL", "imagen-4.0-generate-001")
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:predict?key={api_key}")
    payload = {"instances": [{"prompt": prompt}],
               "parameters": {"sampleCount": 1, "aspectRatio": "3:4"}}
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    b64 = data["predictions"][0]["bytesBase64Encoded"]
    Path(out_path).write_bytes(base64.b64decode(b64))
    return out_path


def _gemini_multiref(prompt: str, reference_images: List[str], out_path: str) -> str:
    import httpx
    api_key = os.getenv("GOOGLE_API_KEY") or os.environ["GEMINI_API_KEY"]
    model = os.getenv("IMAGE_EDIT_MODEL", "gemini-2.0-flash-preview-image-generation")
    parts: List[dict] = [{"text":
        "Объедини эти юбки в ОДИН новый цельный образ юбки. " + prompt}]
    media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png", ".webp": "image/webp"}
    for r in reference_images:
        if r and Path(r).exists():
            ext = Path(r).suffix.lower()
            parts.append({"inline_data": {
                "mime_type": media_map.get(ext, "image/jpeg"),
                "data": base64.b64encode(Path(r).read_bytes()).decode()}})
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    payload = {"contents": [{"role": "user", "parts": parts}],
               "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]}}
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    for part in data["candidates"][0]["content"]["parts"]:
        inline = part.get("inline_data") or part.get("inlineData")
        if inline and inline.get("data"):
            Path(out_path).write_bytes(base64.b64decode(inline["data"]))
            return out_path
    raise RuntimeError("Gemini не вернул изображение")


def generate_concept(features: Dict,
                     reference_images: Optional[List[str]] = None,
                     out_path: Optional[str] = None,
                     provider: Optional[str] = None) -> Dict:
    reference_images = reference_images or []
    prompt = build_concept_prompt(features)
    import tempfile
    out_path = out_path or os.path.join(tempfile.gettempdir(), f"concept_{int(time.time()*1000)}.png")
    p = _resolve_provider(provider)
    if p == "gemini":
        try:
            if reference_images:
                path = _gemini_multiref(prompt, reference_images, out_path)
            else:
                path = _gemini_imagen(prompt, out_path)
            return {"path": path, "provider": "gemini", "prompt": prompt}
        except Exception as e:
            import traceback
            traceback.print_exc()
            path = _mock_render(prompt, reference_images, out_path)
            return {"path": path, "provider": "gemini-fallback",
                    "prompt": prompt, "error": f"{type(e).__name__}: {e}"}
    path = _mock_render(prompt, reference_images, out_path)
    return {"path": path, "provider": "mock", "prompt": prompt}
