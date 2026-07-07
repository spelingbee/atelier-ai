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

# Add parent path to sys.path
sys.path.append(str(Path(__file__).parent.absolute()))

import concept

def test_openai_generation():
    print("Testing OpenAI Image Generation...")
    
    # 1. Check API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[FAIL] OPENAI_API_KEY is not set in .env")
        sys.exit(1)
        
    print(f"Using API Key: {api_key[:12]}...{api_key[-12:]}")
    
    # 2. Define test features for a skirt
    features = {
        "skirt_type": "pencil",
        "estimated_length": "midi",
        "has_pleats": False,
        "has_godets": False,
        "has_wrap": False,
        "has_yoke": True,
        "has_pockets": True,
        "silhouette_notes": "high-waisted pencil skirt with elegant yoke and cargo side pockets, beige wool fabric"
    }
    
    # 3. Call generate_concept
    out_path = str(Path(__file__).parent / "test_concept_openai.png")
    if os.path.exists(out_path):
        os.unlink(out_path)
        
    print("Sending request to DALL-E 3...")
    result = concept.generate_concept(features, out_path=out_path, provider="openai")
    
    # 4. Check result
    provider = result.get("provider")
    print(f"Returned provider: {provider}")
    
    if provider == "openai":
        if os.path.exists(out_path) and os.path.getsize(out_path) > 1000:
            print(f"[OK] Concept image successfully generated at: {out_path}")
            print(f"File size: {os.path.getsize(out_path)} bytes")
            print("OpenAI Image Generation test: SUCCESS")
        else:
            print("[FAIL] Image file was not created or is empty.")
            sys.exit(1)
    else:
        print(f"[FAIL] Ended up with provider: {provider}. Error: {result.get('error')}")
        sys.exit(1)

if __name__ == "__main__":
    test_openai_generation()
