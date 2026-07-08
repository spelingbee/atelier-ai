"""
AtelierAI — МУЛЬТИ-ПРОВАЙДЕРНЫЙ КЛАССИФИКАТОР (NEW FILE, аддитивно).

Два ИИ на выбор для классификации фото юбки:
  - "anthropic"  — Claude (tool use → валидный JSON);
  - "gemini"     — Google Gemini (responseSchema → валидный JSON).
Выбор провайдера: аргумент provider=... или ENV AI_PROVIDER.
Без ключей — оффлайн-mock (разработка и тесты без сети).

ENV:
  AI_PROVIDER          anthropic | gemini | mock   (авто: кто имеет ключ)
  ANTHROPIC_API_KEY    ключ Claude
  ANTHROPIC_MODEL      claude-sonnet-4-5 (дефолт)
  GOOGLE_API_KEY       (или GEMINI_API_KEY) ключ Gemini
  GEMINI_MODEL         gemini-2.0-flash (дефолт)

httpx импортируется лениво — модуль работает даже без установленного httpx.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Dict, List, Optional

# Полный список типов (базовые 5 + skirt_types_extra + skirt_types_more)
ALLOWED_TYPES: List[str] = [
    "straight", "pencil", "a_line", "half_circle", "full_circle",
    "pleated", "tiered", "yoke",
    "tulip", "mermaid", "hi_low", "bubble", "skort", "culottes", "gored_6",
]
LENGTH_HINT_CM = {"mini": 40, "knee": 55, "midi": 70, "maxi": 95}
_MEDIA = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
          ".png": "image/png", ".webp": "image/webp"}

SYSTEM_PROMPT = (
    "You classify women's skirt photos for a pattern-making service. "
    "Pick the closest skirt_type from the allowed list. If unsure, give the best "
    "guess with low confidence. Never invent measurements — only describe what is "
    "visible. "
    "Also, analyze the visual design and: "
    "1. Recommend appropriate fabrics (e.g. density, texture, weave) in Russian (fabric_recommendation). "
    "2. Estimate how closely our pattern-making engine can recreate this design on a scale of 0 to 100 (similarity_percentage). "
    "   Be extremely honest: basic shapes/gored/tiered get 90-100%, wrap with cargo/crossover waistbands get 80-90%, but complex "
    "   asymmetric draping, spiral folds, or custom side godet contrast panels get 30-65% similarity. "
    "3. Briefly explain this percentage in Russian (similarity_explanation) identifying what can be built perfectly "
    "   and what will be simplified or omitted. "
    "4. Provide a technical specification / preparation sewing notes (ТЗ) in Russian (technical_specification_notes)."
)

# Схема полей (общая для обоих провайдеров)
_FIELDS = {
    "skirt_type": ("string", ALLOWED_TYPES),
    "estimated_length": ("string", ["mini", "knee", "midi", "maxi"]),
    "has_waistband": ("boolean", None),
    "has_pleats": ("boolean", None),
    "pleat_count": ("integer", None),
    "n_tiers": ("integer", None),
    "has_yoke": ("boolean", None),
    "has_godets": ("boolean", None),
    "n_godets": ("integer", None),
    "has_wrap": ("boolean", None),
    "has_pockets": ("boolean", None),
    "silhouette_notes": ("string", None),
    "confidence": ("number", None),
    "fabric_recommendation": ("string", None),
    "similarity_percentage": ("integer", None),
    "similarity_explanation": ("string", None),
    "technical_specification_notes": ("string", None),
}
_REQUIRED = [
    "skirt_type", "estimated_length", "has_waistband", "confidence",
    "fabric_recommendation", "similarity_percentage", "similarity_explanation",
    "technical_specification_notes"
]


def _anthropic_schema() -> dict:
    props = {}
    for k, (t, enum) in _FIELDS.items():
        props[k] = {"type": t}
        if enum:
            props[k]["enum"] = enum
    return {"type": "object", "properties": props, "required": _REQUIRED}


def _gemini_schema() -> dict:
    # Gemini OpenAPI-subset: типы ВЕРХНИМ регистром
    type_map = {"string": "STRING", "boolean": "BOOLEAN",
                "integer": "INTEGER", "number": "NUMBER"}
    props = {}
    for k, (t, enum) in _FIELDS.items():
        props[k] = {"type": type_map[t]}
        if enum:
            props[k]["enum"] = enum
    return {"type": "OBJECT", "properties": props, "required": _REQUIRED}


def _sanitize(result: Dict) -> Dict:
    if result.get("skirt_type") not in ALLOWED_TYPES:
        result["skirt_type"] = "straight"
        result["confidence"] = min(float(result.get("confidence", 0.4)), 0.4)
    result.setdefault("estimated_length", "knee")
    result.setdefault("has_waistband", True)
    result.setdefault("has_pleats", False)
    result.setdefault("pleat_count", 0)
    result.setdefault("n_tiers", 0)
    result.setdefault("has_yoke", False)
    result.setdefault("has_godets", False)
    result.setdefault("has_wrap", False)
    result.setdefault("has_pockets", False)
    result.setdefault("silhouette_notes", "")
    conf = float(result.get("confidence", 0.5))
    if conf > 1.0:
        conf = conf / 100.0
    result["confidence"] = conf
    result["length_hint_cm"] = LENGTH_HINT_CM.get(result["estimated_length"], 60)
    
    # New fields defaults
    result.setdefault("fabric_recommendation", "Рекомендуется плотная костюмная ткань, шерсть или деним.")
    try:
        result["similarity_percentage"] = int(result.get("similarity_percentage", 85))
    except Exception:
        result["similarity_percentage"] = 85
    result.setdefault("similarity_explanation", "Основа силуэта строится корректно, карманы и кокетки полностью соответствуют.")
    result.setdefault("technical_specification_notes", "Техническое задание на пошив базовой юбки со стандартной сборкой деталей.")
    return result


def _read_image(image_path: str):
    ext = Path(image_path).suffix.lower()
    media = _MEDIA.get(ext, "image/jpeg")
    img_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    return media, img_b64


# --------------------------------------------------------------------------- #
#  Провайдеры
# --------------------------------------------------------------------------- #
def _resolve_provider(provider: Optional[str]) -> str:
    if provider:
        return provider.lower()
    env = os.getenv("AI_PROVIDER")
    if env:
        return env.lower()
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return "gemini"
    return "mock"


def mock_classify(image_path: str, provider: str = "mock") -> Dict:
    """Детерминировано по имени файла — для воспроизводимых тестов."""
    name = Path(image_path).stem.lower()
    guess = next((t for t in ALLOWED_TYPES if t in name), "a_line")
    res = _sanitize({
        "skirt_type": guess, "estimated_length": "midi",
        "has_waistband": True, "silhouette_notes": f"offline mock ({provider})",
        "confidence": 0.66,
    })
    res["_provider"] = provider
    return res


async def _classify_anthropic(image_path: str) -> Dict:
    import httpx
    api_key = os.environ["ANTHROPIC_API_KEY"]
    media, img_b64 = _read_image(image_path)
    tool = {"name": "report_skirt",
            "description": "Return structured parameters of the skirt.",
            "input_schema": _anthropic_schema()}
    payload = {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        "max_tokens": 500, "system": SYSTEM_PROMPT,
        "tools": [tool], "tool_choice": {"type": "tool", "name": "report_skirt"},
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                          "media_type": media, "data": img_b64}},
            {"type": "text", "text": "Classify this skirt."}]}],
    }
    async with httpx.AsyncClient(timeout=40.0) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"}, json=payload)
        resp.raise_for_status()
        data = resp.json()
    tool_input = next(b["input"] for b in data["content"] if b["type"] == "tool_use")
    res = _sanitize(dict(tool_input))
    res["_provider"] = "anthropic"
    return res


async def _classify_gemini(image_path: str) -> Dict:
    import httpx
    api_key = os.getenv("GOOGLE_API_KEY") or os.environ["GEMINI_API_KEY"]
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    media, img_b64 = _read_image(image_path)
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [
            {"inline_data": {"mime_type": media, "data": img_b64}},
            {"text": "Classify this skirt and return the structured JSON."}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": _gemini_schema(),
            "temperature": 0,
        },
    }
    async with httpx.AsyncClient(timeout=40.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    res = _sanitize(json.loads(text))
    res["_provider"] = "gemini"
    return res


async def _classify_openai(image_path: str) -> Dict:
    import httpx
    api_key = os.environ["OPENAI_API_KEY"]
    model = os.getenv("OPENAI_CLASSIFY_MODEL", "gpt-4o-mini")
    media, img_b64 = _read_image(image_path)
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": "Classify this skirt and return the structured JSON."},
                {"type": "image_url", "image_url": {"url": f"data:{media};base64,{img_b64}"}}
            ]}
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "report_skirt",
                "schema": _anthropic_schema()
            }
        },
        "temperature": 0
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(timeout=40.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenAI API error {resp.status_code}: {resp.text}")
        data = resp.json()
    text = data["choices"][0]["message"]["content"]
    res = _sanitize(json.loads(text))
    res["_provider"] = "openai"
    return res


async def classify_skirt_image(image_path: str,
                               provider: Optional[str] = None) -> Dict:
    """Главная точка входа. provider: anthropic | gemini | openai | mock | None(авто)."""
    p = _resolve_provider(provider)
    try:
        if p == "anthropic":
            return await _classify_anthropic(image_path)
        if p == "gemini":
            return await _classify_gemini(image_path)
        if p == "openai":
            return await _classify_openai(image_path)
        return mock_classify(image_path, "mock")
    except Exception as e:  # сеть/ключ упали — не роняем пайплайн
        res = mock_classify(image_path, f"{p}-fallback")
        res["silhouette_notes"] = f"fallback after error: {type(e).__name__}: {e}"
        return res


async def classify_with_both(image_path: str) -> Dict:
    """Запустить ОБА ИИ и сравнить (для A/B тестов точности).

    Возвращает {anthropic, gemini, agree, chosen}.
    """
    import asyncio
    a, g = await asyncio.gather(
        classify_skirt_image(image_path, "anthropic"),
        classify_skirt_image(image_path, "gemini"),
        return_exceptions=True,
    )
    a = a if isinstance(a, dict) else {"error": str(a)}
    g = g if isinstance(g, dict) else {"error": str(g)}
    agree = a.get("skirt_type") == g.get("skirt_type")
    # выбираем более уверенный
    chosen = a if a.get("confidence", 0) >= g.get("confidence", 0) else g
    return {"anthropic": a, "gemini": g, "agree": agree, "chosen": chosen}
