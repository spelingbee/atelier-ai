"""
AtelierAI — СБОРКА ВСЕГО ВМЕСТЕ (NEW FILE, аддитивно). Ничего не редактирует.

Запуск:  uvicorn app_ext:app --reload --port 8000

Что подключает:
  - базовый app из api.py (старые v1-эндпоинты);
  - новые типы юбок (skirt_types_extra) — pleated/tiered/yoke;
  - надёжный припуск на швы shapely.buffer (seam_shapely);
  - расширенные v2-эндпоинты (api_ext): два ИИ + ИИ-картинки.

ENV для переключения ИИ (два провайдера):
  AI_PROVIDER=gemini        # или anthropic / mock
  GOOGLE_API_KEY=...        # ключ Google (Gemini) — можно тестировать вместо Claude
  GEMINI_MODEL=gemini-2.0-flash
  ANTHROPIC_API_KEY=...     # ключ Claude (если нужен второй ИИ)
  IMAGE_PROVIDER=gemini     # или mock
"""
from __future__ import annotations

import os
from pathlib import Path
_env = Path(__file__).parent / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ[_k.strip()] = _v.strip().strip('"').strip("'")

# 1) надёжный припуск на швы (монки-патч export.seam_outline)
import seam_shapely  # noqa: F401  (авто-патч при импорте)
# 2) новые типы юбок (авто-регистрация в PATTERN_REGISTRY)
import skirt_types_extra  # noqa: F401  (pleated/tiered/yoke)
import skirt_types_more   # noqa: F401  (tulip/mermaid/hi_low/bubble/skort)

# 3) базовый приложение + расширенные роутеры
from api import app  # существующий FastAPI app
from api_ext import router as ext_router
from remix_api import router as remix_router

app.include_router(ext_router)
app.include_router(remix_router)


@app.get("/api/v2/health")
def health_ext():
    import os
    return {
        "status": "ok",
        "ai_provider": os.getenv("AI_PROVIDER", "auto"),
        "image_provider": os.getenv("IMAGE_PROVIDER", "auto"),
        "has_anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "has_google_key": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
    }
