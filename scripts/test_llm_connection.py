import os
import sys
from pathlib import Path
from openai import OpenAI

# Find project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def load_env():
    env_path = PROJECT_ROOT / '.env'
    print(f"Loading .env from: {env_path}")
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()
                # print(f"Set env: {k.strip()}")

def test_llm_connection():
    load_env()
    
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("BASE_URL") or "https://api.siliconflow.cn/v1"
    model = os.getenv("MODEL") or "Qwen/Qwen2.5-7B-Instruct"
    
    print("-" * 50)
    print(f"API Key (masked): {api_key[:8] if api_key else 'None'}...")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print("-" * 50)
    
    if not api_key:
        print("Error: OPENAI_API_KEY not set.")
        return

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        
        print(f"Sending test request to {model}...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, are you working? Please reply with 'Yes, I am working.'"}
            ],
            max_tokens=50
        )
        
        content = response.choices[0].message.content
        print(f"Response: {content}")
        print("-" * 50)
        print("Test Result: SUCCESS ✅")
        
    except Exception as e:
        print(f"Error: {e}")
        print("-" * 50)
        print("Test Result: FAILED ❌")

if __name__ == "__main__":
    test_llm_connection()
