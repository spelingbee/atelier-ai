"""
AtelierAI — AI classifier wrapper.
Delegates to the multi-provider implementation in ai_providers.py.
"""
from __future__ import annotations
from typing import Dict
import ai_providers

async def classify_skirt_image(image_path: str) -> Dict:
    return await ai_providers.classify_skirt_image(image_path)
