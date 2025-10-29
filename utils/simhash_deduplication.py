#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimHash文件去重系统
实现基于SimHash算法的文件相似度检测，用于识别轻微修改的文件
"""

import hashlib
import re
import json
import logging
from typing import List, Tuple, Dict, Optional, Set
from collections import defaultdict
import jieba
import os

logger = logging.getLogger(__name__)

class SimHashDeduplication:
    """SimHash去重系统核心类"""
    
    def __init__(self, hash_bits: int = 64, similarity_threshold: float = 0.85):
        """
        初始化SimHash去重系统
        
        Args:
            hash_bits: SimHash位数，默认64位
            similarity_threshold: 相似度阈值，默认0.85
        """
        self.hash_bits = hash_bits
        self.similarity_threshold = similarity_threshold
        
        # 停用词列表（可扩展）
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很',
            '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '他', '她', '它'
        }
    
    def extract_features(self, text: str) -> List[str]:
        """
        从文本中提取特征词
        
        Args:
            text: 输入文本
            
        Returns:
            特征词列表
        """
        if not text:
            return []
        
        # 清理文本
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text.lower())
        text = re.sub(r'\s+', ' ', text).strip()
        
        # 中英文分词
        features = []
        
        # 中文分词
        chinese_text = re.findall(r'[\u4e00-\u9fff]+', text)
        for segment in chinese_text:
            words = jieba.lcut(segment)
            features.extend([word for word in words if len(word) > 1 and word not in self.stop_words])
        
        # 英文分词
        english_text = re.findall(r'[a-zA-Z]+', text)
        features.extend([word for word in english_text if len(word) > 2 and word not in self.stop_words])
        
        # 数字特征
        numbers = re.findall(r'\d+', text)
        features.extend(numbers)
        
        return features
    
    def calculate_feature_hash(self, feature: str) -> int:
        """
        计算特征的哈希值
        
        Args:
            feature: 特征字符串
            
        Returns:
            哈希值
        """
        return int(hashlib.md5(feature.encode('utf-8')).hexdigest(), 16)
    
    def calculate_simhash(self, text: str) -> int:
        """
        计算文本的SimHash值
        
        Args:
            text: 输入文本
            
        Returns:
            SimHash值
        """
        features = self.extract_features(text)
        
        if not features:
            return 0
        
        # 统计特征词频
        feature_weights = defaultdict(int)
        for feature in features:
            feature_weights[feature] += 1
        
        # 初始化位向量
        bit_vector = [0] * self.hash_bits
        
        # 计算每个特征的贡献
        for feature, weight in feature_weights.items():
            feature_hash = self.calculate_feature_hash(feature)
            
            # 对每一位进行加权
            for i in range(self.hash_bits):
                bit = (feature_hash >> i) & 1
                if bit == 1:
                    bit_vector[i] += weight
                else:
                    bit_vector[i] -= weight
        
        # 生成最终的SimHash
        simhash = 0
        for i in range(self.hash_bits):
            if bit_vector[i] > 0:
                simhash |= (1 << i)
        
        return simhash
    
    def calculate_hamming_distance(self, hash1: int, hash2: int) -> int:
        """
        计算两个哈希值的汉明距离
        
        Args:
            hash1: 第一个哈希值
            hash2: 第二个哈希值
            
        Returns:
            汉明距离
        """
        xor_result = hash1 ^ hash2
        distance = 0
        
        while xor_result:
            distance += xor_result & 1
            xor_result >>= 1
        
        return distance
    
    def calculate_similarity(self, hash1: int, hash2: int) -> float:
        """
        计算两个哈希值的相似度
        
        Args:
            hash1: 第一个哈希值
            hash2: 第二个哈希值
            
        Returns:
            相似度 (0-1之间)
        """
        hamming_distance = self.calculate_hamming_distance(hash1, hash2)
        similarity = 1.0 - (hamming_distance / self.hash_bits)
        return similarity
    
    def extract_text_from_json(self, json_data: dict) -> str:
        """
        从JSON数据中提取文本内容
        
        Args:
            json_data: JSON数据
            
        Returns:
            提取的文本内容
        """
        text_parts = []
        
        def extract_recursive(obj, depth=0):
            if depth > 10:  # 防止过深递归
                return
            
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and len(value) > 10:
                        # 过滤掉URL、时间戳等
                        if not re.match(r'^https?://', value) and not re.match(r'^\d{4}-\d{2}-\d{2}', value):
                            text_parts.append(value)
                    elif isinstance(value, (dict, list)):
                        extract_recursive(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    extract_recursive(item, depth + 1)
            elif isinstance(obj, str) and len(obj) > 10:
                text_parts.append(obj)
        
        extract_recursive(json_data)
        return ' '.join(text_parts)
    
    def calculate_file_simhash(self, file_path: str) -> Optional[int]:
        """
        计算文件的SimHash值
        
        Args:
            file_path: 文件路径
            
        Returns:
            SimHash值，如果计算失败返回None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.endswith('.json'):
                    data = json.load(f)
                    text = self.extract_text_from_json(data)
                else:
                    text = f.read()
            
            return self.calculate_simhash(text)
        
        except Exception as e:
            logger.error(f"计算文件SimHash失败 {file_path}: {e}")
            return None
    
    def is_similar_file(self, file_path: str, processed_simhashes: Dict[str, int]) -> Tuple[bool, Optional[str], float]:
        """
        检查文件是否与已处理的文件相似
        
        Args:
            file_path: 待检查的文件路径
            processed_simhashes: 已处理文件的SimHash字典 {文件路径: SimHash值}
            
        Returns:
            (是否相似, 相似文件路径, 相似度)
        """
        current_simhash = self.calculate_file_simhash(file_path)
        
        if current_simhash is None:
            return False, None, 0.0
        
        max_similarity = 0.0
        most_similar_file = None
        
        for processed_file, processed_simhash in processed_simhashes.items():
            similarity = self.calculate_similarity(current_simhash, processed_simhash)
            
            if similarity > max_similarity:
                max_similarity = similarity
                most_similar_file = processed_file
        
        is_similar = max_similarity >= self.similarity_threshold
        
        if is_similar:
            logger.info(f"发现相似文件: {file_path} 与 {most_similar_file} 相似度: {max_similarity:.3f}")
        
        return is_similar, most_similar_file, max_similarity

# 全局SimHash实例
_simhash_instance = None

def get_simhash_instance() -> SimHashDeduplication:
    """获取全局SimHash实例（单例模式）"""
    global _simhash_instance
    if _simhash_instance is None:
        # 从环境变量读取配置
        hash_bits = int(os.getenv("SIMHASH_BITS", "64"))
        similarity_threshold = float(os.getenv("SIMHASH_SIMILARITY_THRESHOLD", "0.85"))
        _simhash_instance = SimHashDeduplication(hash_bits, similarity_threshold)
    return _simhash_instance

def calculate_file_simhash(file_path: str) -> Optional[int]:
    """便捷函数：计算文件SimHash"""
    simhash = get_simhash_instance()
    return simhash.calculate_file_simhash(file_path)

def check_file_similarity(file_path: str, processed_simhashes: Dict[str, int]) -> Tuple[bool, Optional[str], float]:
    """便捷函数：检查文件相似度"""
    simhash = get_simhash_instance()
    return simhash.is_similar_file(file_path, processed_simhashes)