"""
AtelierAI — AI classifier wrapper.
Delegates to the multi-provider implementation in ai_providers.py.
"""
from __future__ import annotations
from typing import Dict, Optional
import ai_providers

async def classify_skirt_image(image_path: str, provider: Optional[str] = None) -> Dict:
    return await ai_providers.classify_skirt_image(image_path, provider=provider)

