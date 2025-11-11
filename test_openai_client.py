#!/usr/bin/env python3
"""
测试OpenAI客户端连接
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

# 加载环境变量
load_dotenv()

print("🔍 检查环境变量...")
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("BASE_URL")

print(f"API_KEY: {'已设置' if api_key else '未设置'}")
print(f"BASE_URL: {base_url}")

if not api_key:
    print("❌ OPENAI_API_KEY 未设置")
    exit(1)

try:
    print("\n🔄 初始化OpenAI客户端...")
    openai_client = OpenAI(api_key=api_key, base_url=base_url)
    print("✅ OpenAI客户端初始化成功")
    
    print("\n🔄 测试简单API调用...")
    response = openai_client.chat.completions.create(
        model="Qwen/Qwen3-30B-A3B",
        messages=[
            {"role": "user", "content": "Hello, this is a test. Please respond with 'Test successful'."}
        ],
        max_tokens=50,
        temperature=0.1
    )
    
    print("✅ API调用成功")
    print(f"响应: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"❌ API调用失败: {e}")
    import traceback
    print(f"详细错误: {traceback.format_exc()}")