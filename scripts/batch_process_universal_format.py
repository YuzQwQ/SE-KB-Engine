#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理原始数据，按照通用知识库格式生成知识库文件
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
from utils.simhash_deduplication import get_simhash_instance, calculate_file_simhash, check_file_similarity

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('batch_process.log', encoding='utf-8'),
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
    """检查文件是否已经处理过（支持MD5和SimHash双重检测）"""
    file_path_str = str(file_path)
    file_hash = get_file_hash(file_path)
    
    if not file_hash:
        return False
    
    # 1. 精确匹配检查（MD5哈希）
    if file_path_str in processed_record:
        recorded_hash = processed_record[file_path_str].get('hash')
        if recorded_hash == file_hash:
            logger.info(f"文件已处理过（精确匹配），跳过: {file_path.name}")
            return True
        else:
            logger.info(f"文件已修改，重新处理: {file_path.name}")
    
    # 2. 相似度检查（SimHash）
    try:
        # 提取所有已处理文件的SimHash值
        processed_simhashes = {}
        for processed_file, record_data in processed_record.items():
            simhash_value = record_data.get('simhash')
            if simhash_value is not None:
                processed_simhashes[processed_file] = simhash_value
        
        if processed_simhashes:
            is_similar, similar_file, similarity = check_file_similarity(file_path_str, processed_simhashes)
            if is_similar:
                logger.info(f"发现相似文件，跳过: {file_path.name} (与 {os.path.basename(similar_file)} 相似度: {similarity:.3f})")
                return True
    
    except Exception as e:
        logger.warning(f"SimHash相似度检查失败: {e}")
    
    return False

def mark_file_processed(file_path, processed_record):
    """标记文件为已处理（包含MD5和SimHash）"""
    file_path_str = str(file_path)
    file_hash = get_file_hash(file_path)
    
    if file_hash:
        # 计算SimHash值
        simhash_value = None
        try:
            simhash_value = calculate_file_simhash(file_path_str)
        except Exception as e:
            logger.warning(f"计算SimHash失败 {file_path.name}: {e}")
        
        processed_record[file_path_str] = {
            'hash': file_hash,
            'simhash': simhash_value,
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
        if is_valid_text_content(content_data):
            logger.debug("内容已经是有效的文本格式")
            return content_data
        
        # 检查是否包含二进制数据的特征
        if '\\x' in content_data or len(content_data.encode('utf-8', errors='ignore')) != len(content_data):
            try:
                # 尝试Brotli解压缩
                # 首先尝试直接解压缩（假设是原始二进制数据的字符串表示）
                if content_data.startswith('[') and '\\x' in content_data:
                    # 处理类似 '[tO\\x11EY...' 的格式
                    # 移除开头的 '[' 和结尾的可能字符
                    clean_data = content_data.strip('[]"\'')
                    # 将转义的十六进制字符转换为字节
                    try:
                        # 使用正则表达式替换 \\x 为实际的十六进制字节
                        import codecs
                        clean_data = codecs.decode(clean_data, 'unicode_escape')
                        # 将字符串编码为latin-1然后解压缩
                        binary_data = clean_data.encode('latin-1')
                        decompressed = brotli.decompress(binary_data)
                        result = decompressed.decode('utf-8', errors='ignore')
                        logger.info(f"[SUCCESS] 使用Brotli成功解压缩，结果长度: {len(result)} 字符")
                        return result
                    except Exception as e:
                        logger.warning(f"Brotli解压缩失败: {e}")
                
                # 尝试其他解压缩方法
                try:
                    # 尝试base64解码后解压缩
                    if content_data.replace('\\x', '').replace('[', '').replace(']', '').isalnum():
                        decoded = base64.b64decode(content_data.replace('\\x', '').replace('[', '').replace(']', ''))
                        decompressed = brotli.decompress(decoded)
                        result = decompressed.decode('utf-8', errors='ignore')
                        logger.info(f"[SUCCESS] 使用base64+Brotli成功解压缩，结果长度: {len(result)} 字符")
                        return result
                except Exception as e:
                    logger.debug(f"base64+Brotli解压缩失败: {e}")
                    pass
                    
            except Exception as e:
                logger.warning(f"内容解压缩失败: {e}")
                return None
        
        # 尝试将字符串作为base64解码
        try:
            decoded_data = base64.b64decode(content_data)
            content_data = decoded_data
            logger.debug("成功将字符串解码为base64")
        except Exception as e:
            logger.debug(f"base64解码失败: {e}")
            return content_data  # 如果解码失败，返回原始字符串
    
    if isinstance(content_data, bytes):
        # 尝试不同的解压缩方法
        decompression_methods = [
            ('brotli', lambda x: brotli.decompress(x).decode('utf-8', errors='ignore')),
            ('gzip', lambda x: gzip.decompress(x).decode('utf-8', errors='ignore')),
            ('zlib', lambda x: zlib.decompress(x).decode('utf-8', errors='ignore')),
            ('raw_utf8', lambda x: x.decode('utf-8', errors='ignore')),
            ('raw_latin1', lambda x: x.decode('latin-1', errors='ignore'))
        ]
        
        for method_name, method in decompression_methods:
            try:
                result = method(content_data)
                if result and is_valid_text_content(result):
                    logger.info(f"[SUCCESS] 使用 {method_name} 成功解压缩，结果长度: {len(result)} 字符")
                    return result
                else:
                    logger.debug(f"使用 {method_name} 解压缩成功但内容无效")
            except Exception as e:
                logger.debug(f"使用 {method_name} 解压缩失败: {e}")
                continue
    
    # 如果是字符串但包含转义字符，尝试处理
    if isinstance(content_data, str):
        try:
            # 尝试处理转义字符
            processed = content_data.encode().decode('unicode_escape')
            if is_valid_text_content(processed):
                logger.debug("成功处理转义字符")
                return processed
        except Exception as e:
            logger.debug(f"处理转义字符失败: {e}")
            pass
    
    logger.warning("所有解压缩方法都失败")
    return content_data if isinstance(content_data, str) else str(content_data)

def is_valid_text_content(content):
    """
    检查内容是否为有效的文本内容
    """
    if not content or not isinstance(content, str):
        return False
    
    # 检查是否包含过多的二进制字符
    binary_chars = sum(1 for c in content if ord(c) < 32 and c not in '\n\r\t')
    if len(content) > 0 and binary_chars / len(content) > 0.1:  # 如果超过10%是二进制字符
        return False
    
    # 检查是否包含可读文本
    readable_chars = sum(1 for c in content if c.isprintable() or c in '\n\r\t')
    if len(content) > 0 and readable_chars / len(content) < 0.7:  # 如果少于70%是可读字符
        return False
    
    return True

def process_json_file(file_path, processor):
    """
    处理单个JSON文件，使用通用知识库格式
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取文件名作为主题
        file_name = Path(file_path).stem
        topic = file_name.replace('_parsed', '').replace('google_', '')
        
        # 根据数据结构提取内容
        content = ""
        source_url = ""
        
        if isinstance(data, dict):
            if 'organic_results' in data:  # SerpAPI格式数据
                # 处理SerpAPI格式的搜索结果
                results_text = []
                for result in data.get('organic_results', []):
                    if isinstance(result, dict):
                        title = result.get('title', '').strip()
                        snippet = result.get('snippet', '').strip()
                        
                        # 清理标题和摘要，只保留有意义的文本
                        if title:
                            title = re.sub(r'[{}\[\]"\':,;]', ' ', title)
                            title = re.sub(r'\s+', ' ', title).strip()
                        if snippet:
                            snippet = re.sub(r'[{}\[\]"\':,;]', ' ', snippet)
                            snippet = re.sub(r'\s+', ' ', snippet).strip()
                        
                        if title and snippet:
                            results_text.append(f"{title}: {snippet}")
                        elif title:
                            results_text.append(title)
                        elif snippet:
                            results_text.append(snippet)
                
                content = '\n'.join(results_text)
                # 进一步清理内容，移除JSON字段名残留
                content = re.sub(r'\b(position|redirect_link|displayed_link|favicon|snippet_highlighted_words|source|search_metadata|search_parameters|organic_results|pagination)\b:?', '', content)
                content = re.sub(r'\s+', ' ', content).strip()
                
                # 获取搜索URL
                search_metadata = data.get('search_metadata', {})
                source_url = search_metadata.get('google_url', 'unknown')
            elif 'results' in data:  # 传统Google搜索结果格式
                # 正确处理搜索结果，避免JSON乱码
                results_text = []
                for result in data['results']:
                    title = result.get('title', '').strip()
                    snippet = result.get('snippet', '').strip()
                    
                    # 清理标题和摘要中的特殊字符和JSON残留
                    if title:
                        title = re.sub(r'[{}\[\]"\':,;]', ' ', title)
                        title = re.sub(r'\s+', ' ', title).strip()
                    if snippet:
                        snippet = re.sub(r'[{}\[\]"\':,;]', ' ', snippet)
                        snippet = re.sub(r'\s+', ' ', snippet).strip()
                    
                    if title and snippet:
                        results_text.append(f"{title}: {snippet}")
                    elif title:
                        results_text.append(title)
                    elif snippet:
                        results_text.append(snippet)
                
                content = '\n'.join(results_text)
                # 进一步清理内容，移除JSON字段名残留
                content = re.sub(r'\b(position|redirect_link|displayed_link|favicon|snippet_highlighted_words|source|search_metadata|search_parameters|organic_results|pagination)\b:?', '', content)
                content = re.sub(r'\s+', ' ', content).strip()
                source_url = data.get('search_url', 'unknown')
            elif 'raw_data' in data and 'content' in data['raw_data']:  # 原始数据格式
                raw_content = data['raw_data']['content']
                # 尝试解压缩内容
                decompressed_content = decompress_content(raw_content)
                if decompressed_content and is_valid_text_content(decompressed_content):
                    content = decompressed_content
                    source_url = data['raw_data'].get('url', 'unknown')
                    print(f"[SUCCESS] 成功解压缩内容，长度: {len(content)} 字符")
                else:
                    # 如果解压缩失败，尝试使用parsed_data
                    if 'parsed_data' in data and 'content' in data['parsed_data']:
                        parsed_content = data['parsed_data']['content']
                        decompressed_parsed = decompress_content(parsed_content)
                        if decompressed_parsed and is_valid_text_content(decompressed_parsed):
                            content = decompressed_parsed
                            source_url = data['parsed_data'].get('url', data['raw_data'].get('url', 'unknown'))
                            print(f"[SUCCESS] 从parsed_data成功解压缩内容，长度: {len(content)} 字符")
                        else:
                            logger.warning(f"无法解压缩内容，跳过文件: {file_name}")
                            return None
                    else:
                        logger.warning(f"无法解压缩内容且无parsed_data，跳过文件: {file_name}")
                        return None
            elif 'content' in data:  # 解析后的内容格式
                raw_content = data['content']
                decompressed_content = decompress_content(raw_content)
                if decompressed_content and is_valid_text_content(decompressed_content):
                    content = decompressed_content
                else:
                    content = raw_content  # 如果解压缩失败，使用原始内容
                source_url = data.get('url', 'unknown')
            elif 'title' in data and 'snippet' in data:  # 单个搜索结果格式
                content = f"{data['title']}: {data['snippet']}"
                source_url = data.get('url', 'unknown')
            else:
                # 尝试提取所有文本内容
                content = str(data)
                source_url = 'unknown'
        elif isinstance(data, list):
            # 处理列表格式的数据
            content = '\n'.join([str(item) for item in data])
            source_url = 'unknown'
        else:
            content = str(data)
            source_url = 'unknown'
        
        if not content.strip():
            logger.warning(f"文件 {file_path} 内容为空，跳过处理")
            return None
        
        logger.info(f"[FILE] 处理文件: {file_name}")
        logger.info(f"[INFO] 内容长度: {len(content)} 字符")
        logger.info(f"[INFO] 内容预览: {content[:200]}...")
        
        # 如果内容过长，截取前面部分以提高处理速度
        if len(content) > 50000:
            content = content[:50000]
            logger.warning(f"内容过长，截取前50000字符进行处理")
        
        # 使用通用知识处理器提取知识
        knowledge_base = processor.extract_knowledge(
            content=content,
            url=source_url,
            title=topic,
            requirement_type="需求分析",
            target_conversion_type="DFD图"
        )
        
        if not knowledge_base:
            logger.warning(f"文件 {file_path} 未提取到有效知识，跳过")
            return None
        
        # 检查知识库是否包含有效内容
        has_valid_content = False
        for section in ['generation_knowledge', 'validation_knowledge', 'examples']:
            if section in knowledge_base:
                for subsection, items in knowledge_base[section].items():
                    if isinstance(items, list) and len(items) > 0:
                        has_valid_content = True
                        break
                if has_valid_content:
                    break
        
        if not has_valid_content:
            logger.warning(f"文件 {file_path} 提取的知识库为空，但仍保存以记录处理状态")
        
        # 保存到知识库（使用通用格式）
        try:
            result = processor.save_knowledge_base(
                knowledge_base=knowledge_base
            )
            logger.info(f"[SAVE] 保存结果: {result}")
            logger.info(f"[SUCCESS] 成功处理文件: {file_name}")
            return result
        except Exception as save_error:
            logger.error(f"保存知识库时出错: {save_error}")
            return None
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误 - 文件 {file_path}: {e}")
        return None
    except UnicodeDecodeError as e:
        logger.error(f"编码错误 - 文件 {file_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出现未知错误: {e}")
        logger.debug(f"错误详情: {type(e).__name__}: {str(e)}")
        return None

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