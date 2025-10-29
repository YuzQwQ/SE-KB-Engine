#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动化知识库处理触发器
监控data/raw目录，当有新文件时自动触发批量处理
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_process_trigger.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RawDataHandler(FileSystemEventHandler):
    """监控data/raw目录的文件变化"""
    
    def __init__(self):
        self.last_process_time = 0
        self.process_delay = 30  # 30秒延迟，避免频繁触发
        
    def on_created(self, event):
        """当有新文件创建时触发"""
        if event.is_directory:
            return
            
        if event.src_path.endswith('.json'):
            logger.info(f"检测到新的JSON文件: {event.src_path}")
            self.schedule_process()
    
    def on_modified(self, event):
        """当文件被修改时触发"""
        if event.is_directory:
            return
            
        if event.src_path.endswith('.json'):
            logger.info(f"检测到JSON文件修改: {event.src_path}")
            self.schedule_process()
    
    def schedule_process(self):
        """安排处理任务，避免频繁触发"""
        current_time = time.time()
        if current_time - self.last_process_time > self.process_delay:
            self.last_process_time = current_time
            logger.info("安排批量处理任务...")
            # 延迟执行，确保文件写入完成
            time.sleep(5)
            self.trigger_batch_process()
    
    def trigger_batch_process(self):
        """触发批量处理脚本"""
        try:
            script_path = Path(project_root) / "scripts" / "batch_process_universal_format.py"
            if not script_path.exists():
                logger.error(f"批量处理脚本不存在: {script_path}")
                return
            
            logger.info("开始执行批量处理脚本...")
            
            # 执行批量处理脚本
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                encoding='utf-8',
                errors='ignore'  # 忽略编码错误
            )
            
            if result.returncode == 0:
                logger.info("✅ 批量处理脚本执行成功")
                logger.info(f"输出: {result.stdout}")
            else:
                logger.error(f"❌ 批量处理脚本执行失败，返回码: {result.returncode}")
                logger.error(f"错误输出: {result.stderr}")
                
        except Exception as e:
            logger.error(f"执行批量处理脚本时出错: {e}")

def main():
    """主函数"""
    logger.info("🚀 启动自动化知识库处理触发器")
    
    # 检查data/raw目录是否存在
    raw_data_dir = Path(project_root) / "data" / "raw"
    if not raw_data_dir.exists():
        logger.error(f"❌ 原始数据目录不存在: {raw_data_dir}")
        return
    
    logger.info(f"📂 监控目录: {raw_data_dir}")
    
    # 创建文件系统监控器
    event_handler = RawDataHandler()
    observer = Observer()
    observer.schedule(event_handler, str(raw_data_dir), recursive=True)
    
    # 启动监控
    observer.start()
    logger.info("✅ 文件监控已启动，等待新文件...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 收到中断信号，正在停止监控...")
        observer.stop()
    
    observer.join()
    logger.info("👋 自动化触发器已停止")

if __name__ == "__main__":
    main()