#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动自动化知识库处理触发器
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """主函数"""
    logger.info("🚀 启动自动化知识库处理触发器")
    
    # 获取项目根目录
    project_root = Path(__file__).parent
    trigger_script = project_root / "scripts" / "auto_process_trigger.py"
    
    if not trigger_script.exists():
        logger.error(f"❌ 触发器脚本不存在: {trigger_script}")
        return
    
    try:
        # 启动触发器脚本
        logger.info(f"📂 启动脚本: {trigger_script}")
        subprocess.run([sys.executable, str(trigger_script)], cwd=project_root)
        
    except KeyboardInterrupt:
        logger.info("🛑 收到中断信号，正在停止...")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main()