#!/usr/bin/env python
"""
测试 LLM Merger API 配置
"""

import sys
import os
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env
def load_env():
    env_path = project_root / '.env'
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                if k and v and os.getenv(k) is None:
                    os.environ[k] = v

load_env()


def main():
    print("=" * 50)
    print("LLM Merger API 测试")
    print("=" * 50)
    
    # 检查配置
    print("\n[配置检查]")
    api_base = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL") or "https://api.siliconflow.cn/v1"
    api_key = os.getenv("OPENAI_API_KEY", "")
    kb_model_id = os.getenv("KB_MODEL_ID", "")
    kb_model_default = os.getenv("KB_MODEL_DEFAULT", "")
    
    print(f"  OPENAI_API_BASE: {api_base}")
    print(f"  OPENAI_API_KEY: {'已设置 (' + api_key[:8] + '...)' if api_key else '未设置'}")
    print(f"  KB_MODEL_ID: {kb_model_id or '未设置'}")
    print(f"  KB_MODEL_DEFAULT: {kb_model_default or '未设置'}")
    
    # 确定使用的模型
    model_id = kb_model_id or kb_model_default or "Qwen/Qwen3-8B"
    print(f"\n  将使用模型: {model_id}")
    
    if not api_key:
        print("\n[错误] OPENAI_API_KEY 未设置")
        return
    
    # 测试 API 调用
    print("\n[测试 API 调用]")
    
    import httpx
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "user", "content": "请回复'OK'"}
        ],
        "temperature": 0,
        "max_tokens": 10
    }
    
    print(f"  请求 URL: {api_base}/chat/completions")
    print(f"  请求模型: {model_id}")
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{api_base}/chat/completions",
                headers=headers,
                json=payload
            )
            
            print(f"  HTTP 状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print(f"  响应内容: {content}")
                print("\n[成功] API 连接正常!")
            else:
                print(f"  错误响应: {response.text[:500]}")
                print("\n[失败] 请检查 API 配置")
                
    except Exception as e:
        print(f"  异常: {e}")
        print("\n[失败] API 调用失败")


if __name__ == "__main__":
    main()

