import os
import sys
from pathlib import Path

# Load env variables from .env manually
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.strip().startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()

# Add current path to sys.path
sys.path.append(str(Path(__file__).parent.absolute()))

import ai_providers

def create_temp_img():
    import base64
    # 1x1 black pixel png base64
    b64_data = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    img_path = Path(__file__).parent / "temp_test_skirt.png"
    img_path.write_bytes(base64.b64decode(b64_data))
    return str(img_path)

async def test_openai_classify():
    print("Testing OpenAI Skirt Classifier...")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[FAIL] OPENAI_API_KEY is not set in .env")
        sys.exit(1)
        
    img_path = create_temp_img()
    try:
        res = await ai_providers.classify_skirt_image(img_path, provider="openai")
        print("Result keys returned:")
        for k, v in res.items():
            print(f"  {k}: {v}")
        
        # Verify response keys
        assert res.get("_provider") == "openai", f"Expected provider 'openai', got {res.get('_provider')}"
        assert "skirt_type" in res, "skirt_type missing"
        assert "fabric_recommendation" in res, "fabric_recommendation missing"
        assert "similarity_percentage" in res, "similarity_percentage missing"
        assert "technical_specification_notes" in res, "technical_specification_notes missing"
        
        print("OpenAI Classification test: SUCCESS")
    except Exception as e:
        print(f"[FAIL] OpenAI Classification test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if os.path.exists(img_path):
            os.unlink(img_path)

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_openai_classify())
