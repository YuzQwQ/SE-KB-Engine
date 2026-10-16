#!/usr/bin/env python3
"""
启动知识库构建系统 Web 界面
"""

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from se_kb_app.composition import Application


def main(application: "Application | None" = None):
    # 确保在正确的目录
    root = Path(__file__).parent
    web_app = root / "web" / "app.py"

    if not web_app.exists():
        print("[ERROR] 找不到 web/app.py")
        sys.exit(1)

    print("=" * 50)
    print("[SE-KB] 启动知识库构建系统 Web 界面")
    print("=" * 50)
    print()
    print("访问地址: http://localhost:8000")
    print("按 Ctrl+C 停止服务")
    print()
    print("=" * 50)

    if application is None:
        # Compatibility path keeps process isolation for existing operators.
        subprocess.run([sys.executable, str(web_app)], cwd=str(root), check=False)
        return

    from web.app import bind_application

    flask_app = bind_application(application)
    flask_app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
