#!/usr/bin/env python3
"""
启动知识库构建系统 Web 界面
"""

import subprocess
import sys
from pathlib import Path

def main():
    # 确保在正确的目录
    root = Path(__file__).parent
    web_app = root / 'web' / 'app.py'
    
    if not web_app.exists():
        print("❌ 找不到 web/app.py")
        sys.exit(1)
    
    print("=" * 50)
    print("🚀 启动知识库构建系统 Web 界面")
    print("=" * 50)
    print()
    print("📌 访问地址: http://localhost:5000")
    print("📌 按 Ctrl+C 停止服务")
    print()
    print("=" * 50)
    
    # 启动 Flask 应用
    subprocess.run([sys.executable, str(web_app)], cwd=str(root))

if __name__ == '__main__':
    main()


