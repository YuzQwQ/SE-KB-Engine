#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版批量处理原始数据，按照通用知识库格式生成知识库文件
添加了去重机制和增量处理功能
"""

import json
import os
from pathlib import Path
import sys
import brotli
import gzip
import zlib
import base64
import re
import logging
from datetime import datetime
import hashlib

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append('.')

from universal_knowledge_processor import UniversalKnowledgeProcessor
sys.path.append(project_root)
from server import save_to_knowledge_base

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_process_improved.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 处理记录文件
PROCESSED_RECORD_FILE = 'processed_files_record.json'

def load_processed_record():
    """加载已处理文件记录"""
    if os.path.exists(PROCESSED_RECORD_FILE):
        try:
            with open(PROCESSED_RECORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"加载处理记录失败: {e}")
    return {}

def save_processed_record(record):
    """保存已处理文件记录"""
    try:
        with open(PROCESSED_RECORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存处理记录失败: {e}")

def get_file_hash(file_path):
    """计算文件的MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"计算文件哈希失败 {file_path}: {e}")
        return None

def is_file_processed(file_path, processed_record):
    """检查文件是否已经处理过"""
    file_path_str = str(file_path)
    file_hash = get_file_hash(file_path)
    
    if not file_hash:
        return False
    
    # 检查文件路径和哈希值
    if file_path_str in processed_record:
        recorded_hash = processed_record[file_path_str].get('hash')
        if recorded_hash == file_hash:
            logger.info(f"文件已处理过，跳过: {file_path.name}")
            return True
        else:
            logger.info(f"文件已修改，重新处理: {file_path.name}")
    
    return False

def mark_file_processed(file_path, processed_record):
    """标记文件为已处理"""
    file_path_str = str(file_path)
    file_hash = get_file_hash(file_path)
    
    if file_hash:
        processed_record[file_path_str] = {
            'hash': file_hash,
            'processed_time': datetime.now().isoformat(),
            'file_size': os.path.getsize(file_path)
        }

def decompress_content(content_data):
    """
    尝试解压缩内容数据，支持多种压缩格式
    """
    if not content_data:
        logger.warning("接收到空的内容数据")
        return None
    
    logger.debug(f"开始解压缩内容，数据类型: {type(content_data)}, 长度: {len(content_data) if hasattr(content_data, '__len__') else 'N/A'}")
    
    # 如果已经是字符串且可读，直接返回
    if isinstance(content_data, str):
        try:
            # 尝试解析为JSON，验证是否为有效内容
            json.loads(content_data)
            logger.debug("内容已经是有效的JSON字符串")
            return content_data
        except json.JSONDecodeError:
            # 如果不是JSON，但是可读文本，也返回
            if len(content_data) > 10 and content_data.isprintable():
                logger.debug("内容是可读文本字符串")
                return content_data
    
    # 如果是字节数据，尝试各种解压缩方法
    if isinstance(content_data, bytes):
        # 1. 尝试Brotli解压缩
        try:
            decompressed = brotli.decompress(content_data)
            result = decompressed.decode('utf-8')
            logger.debug("使用Brotli解压缩成功")
            return result
        except Exception as e:
            logger.debug(f"Brotli解压缩失败: {e}")
        
        # 2. 尝试gzip解压缩
        try:
            decompressed = gzip.decompress(content_data)
            result = decompressed.decode('utf-8')
            logger.debug("使用gzip解压缩成功")
            return result
        except Exception as e:
            logger.debug(f"gzip解压缩失败: {e}")
        
        # 3. 尝试zlib解压缩
        try:
            decompressed = zlib.decompress(content_data)
            result = decompressed.decode('utf-8')
            logger.debug("使用zlib解压缩成功")
            return result
        except Exception as e:
            logger.debug(f"zlib解压缩失败: {e}")
        
        # 4. 尝试直接解码为UTF-8
        try:
            result = content_data.decode('utf-8')
            logger.debug("直接UTF-8解码成功")
            return result
        except Exception as e:
            logger.debug(f"UTF-8解码失败: {e}")
    
    # 如果是base64编码的字符串，尝试解码
    if isinstance(content_data, str):
        try:
            # 尝试base64解码
            decoded_bytes = base64.b64decode(content_data)
            # 递归调用自己处理解码后的字节数据
            return decompress_content(decoded_bytes)
        except Exception as e:
            logger.debug(f"base64解码失败: {e}")
    
    logger.warning(f"无法解压缩内容数据，类型: {type(content_data)}")
    return None

def is_valid_text_content(content):
    """
    检查内容是否为有效的文本内容
    """
    if not content or not isinstance(content, str):
        return False
    
    # 检查长度
    if len(content.strip()) < 10:
        return False
    
    # 检查是否包含足够的可打印字符
    printable_chars = sum(1 for c in content if c.isprintable() or c.isspace())
    if printable_chars / len(content) < 0.8:
        return False
    
    return True

def process_json_file(file_path, processor):
    """
    处理单个JSON文件
    """
    try:
        logger.info(f"开始处理文件: {file_path}")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.debug(f"成功读取JSON文件，数据类型: {type(data)}")
        
        # 检查数据结构
        if not isinstance(data, dict):
            logger.warning(f"文件格式不正确，期望dict，实际: {type(data)}")
            return False
        
        # 检查是否有results字段
        if 'results' not in data:
            logger.warning(f"文件缺少results字段: {file_path}")
            return False
        
        results = data['results']
        if not isinstance(results, list):
            logger.warning(f"results字段不是列表: {file_path}")
            return False
        
        logger.info(f"找到 {len(results)} 个结果项")
        
        # 处理每个结果项
        processed_count = 0
        for i, result in enumerate(results):
            try:
                logger.debug(f"处理第 {i+1} 个结果项")
                
                # 检查必要字段
                if not isinstance(result, dict):
                    logger.warning(f"结果项 {i+1} 不是字典格式")
                    continue
                
                # 获取URL和内容
                url = result.get('url', '')
                content = result.get('content', '')
                title = result.get('title', '')
                
                if not url:
                    logger.warning(f"结果项 {i+1} 缺少URL")
                    continue
                
                # 处理内容
                if isinstance(content, dict) and 'data' in content:
                    # 内容被压缩存储
                    content_data = content['data']
                    decompressed_content = decompress_content(content_data)
                    
                    if not decompressed_content:
                        logger.warning(f"无法解压缩内容: {url}")
                        continue
                    
                    content = decompressed_content
                
                # 验证内容有效性
                if not is_valid_text_content(content):
                    logger.warning(f"内容无效或太短: {url}")
                    continue
                
                logger.debug(f"内容长度: {len(content)} 字符")
                
                # 使用通用知识处理器处理
                try:
                    knowledge_data = processor.process_content(
                        content=content,
                        url=url,
                        title=title
                    )
                    
                    if knowledge_data:
                        # 保存到知识库
                        save_result = save_to_knowledge_base(knowledge_data)
                        if save_result:
                            processed_count += 1
                            logger.info(f"成功处理并保存: {url}")
                        else:
                            logger.warning(f"保存失败: {url}")
                    else:
                        logger.warning(f"知识处理失败: {url}")
                        
                except Exception as e:
                    logger.error(f"处理内容时出错 {url}: {e}")
                    continue
                    
            except Exception as e:
                logger.error(f"处理结果项 {i+1} 时出错: {e}")
                continue
        
        logger.info(f"文件处理完成: {file_path.name}, 成功处理 {processed_count}/{len(results)} 个项目")
        return processed_count > 0
        
    except Exception as e:
        logger.error(f"处理文件失败 {file_path}: {e}")
        return False

def main():
    """
    批量处理原始数据目录中的所有JSON文件
    """
    # 加载已处理文件记录
    processed_record = load_processed_record()
    logger.info(f"加载已处理文件记录: {len(processed_record)} 个文件")
    
    # 初始化通用知识处理器
    processor = UniversalKnowledgeProcessor()
    print(f"[SUCCESS] 初始化通用知识处理器成功")
    
    # 原始数据目录
    raw_data_dir = Path('data/raw')
    
    if not raw_data_dir.exists():
        print(f"[ERROR] 原始数据目录不存在: {raw_data_dir}")
        return
    
    print(f"[INFO] 开始处理目录: {raw_data_dir}")
    
    # 统计信息
    total_files = 0
    processed_files = 0
    failed_files = 0
    skipped_files = 0
    
    # 遍历所有JSON文件
    json_files = list(raw_data_dir.rglob('*.json'))
    print(f"[INFO] 找到 {len(json_files)} 个JSON文件待处理")
    
    for json_file in json_files:
        total_files += 1
        print(f"\n{'='*50}")
        print(f"[INFO] 处理第 {total_files} 个文件: {json_file.name}")
        
        # 检查是否已处理过
        if is_file_processed(json_file, processed_record):
            skipped_files += 1
            continue
        
        result = process_json_file(json_file, processor)
        
        if result:
            processed_files += 1
            # 标记为已处理
            mark_file_processed(json_file, processed_record)
        else:
            failed_files += 1
    
    # 保存处理记录
    save_processed_record(processed_record)
    
    # 输出统计结果
    print(f"\n{'='*60}")
    print(f"[SUCCESS] 批量处理完成!")
    print(f"[INFO] 总文件数: {total_files}")
    print(f"[SUCCESS] 成功处理: {processed_files}")
    print(f"[INFO] 跳过文件: {skipped_files}")
    print(f"[ERROR] 处理失败: {failed_files}")
    print(f"[INFO] 成功率: {processed_files/(total_files-skipped_files)*100:.1f}%" if (total_files-skipped_files) > 0 else "[INFO] 成功率: 0%")
    
    # 检查生成的知识库文件
    kb_dir = Path('shared_data/knowledge_base')
    if kb_dir.exists():
        kb_files = list(kb_dir.rglob('*.json'))
        print(f"\n[INFO] 知识库文件数量: {len(kb_files)}")
        
        # 按分类统计
        categories = {}
        for kb_file in kb_files:
            category = kb_file.parent.name
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        print(f"[INFO] 按分类统计:")
        for category, count in categories.items():
            print(f"  {category}: {count} 个文件")

if __name__ == "__main__":
    main()