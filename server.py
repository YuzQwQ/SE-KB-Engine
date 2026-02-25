# -*- coding: utf-8 -*-

from config.path_config import MARKDOWN_LLM_READY_DIR
from config.path_config import KNOWLEDGE_BASE_DIR
from config.path_config import JSON_LLM_READY_DIR
import base64
from io import BytesIO
from PIL import Image
import json
import os
from dotenv import load_dotenv
import httpx
from typing import Any, List, Dict
from mcp.server.fastmcp import FastMCP
import logging

# 在导入任何自定义模块之前配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        # Remove StreamHandler to avoid stdout pollution
    ],
    force=True  # 强制重新配置，覆盖任何已存在的配置
)

# 确保所有已存在的 logger 都使用新配置
for name in logging.Logger.manager.loggerDict:
    logger_obj = logging.getLogger(name)
    logger_obj.handlers.clear()
    logger_obj.propagate = True

logger = logging.getLogger(__name__)

# 现在可以安全地导入自定义模块
from vectorizer import VectorConfig, KnowledgeRetriever, QueryIntent, QueryPlanner
from scripts.format_processor import FormatProcessor
from scripts.universal_knowledge_processor import UniversalKnowledgeProcessor
from utils.web_deduplication import get_deduplication_instance, check_and_cache, clean_cache, get_stats
from utils.webpage_storage import get_storage_instance
try:
    from httpx_socks import AsyncProxyTransport
    SOCKS_AVAILABLE = True
except ImportError:
    SOCKS_AVAILABLE = False
    # Warning: httpx-socks not installed, SOCKS proxy functionality will be unavailable
from openai import OpenAI
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import asyncio
from urllib.parse import urljoin, urlparse
import time
import requests  # 添加requests库用于SerpAPI请求
import datetime
import re
from pathlib import Path
import subprocess
import json
import requests

import random
import threading

# 导入MySQL数据库工具
# from mysql_db_utils import init_db, save_to_db, close_pool

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("BASE_URL"))
model = os.getenv("MODEL")

mcp = FastMCP("WebScrapingServer")

# 初始化格式处理器
format_processor = FormatProcessor()
universal_processor = UniversalKnowledgeProcessor()

# 初始化知识检索器和查询规划器
try:
    vector_config = VectorConfig()
    knowledge_retriever = KnowledgeRetriever(vector_config)
    query_planner = QueryPlanner(knowledge_retriever)
    logger.info("KnowledgeRetriever and QueryPlanner initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize KnowledgeRetriever: {e}")
    knowledge_retriever = None
    query_planner = None

# 加载系统提示词配置
def load_system_prompts():
    """加载系统提示词配置文件"""
    try:
        # 优先使用专注版本
        focused_path = Path("config/system_prompts_focused.json")
        if focused_path.exists():
            with open(focused_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # 回退到原始版本
        config_path = Path("config/system_prompts.json")
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"系统提示词配置文件不存在: {config_path}")
            return None
    except Exception as e:
        logger.error(f"加载系统提示词配置失败: {str(e)}")
        return None

def get_system_prompt(prompt_type=None):
    """获取指定类型的系统提示词"""
    prompts_config = load_system_prompts()
    if not prompts_config:
        # 如果配置文件加载失败，返回默认的通用提示词
        return (
            "你是一位专业的网页内容分析专家。你的主要职责是从网页内容中提取和分析有价值的信息。\n\n"
            "请重点关注以下内容：\n"
            "1. 核心概念、定义和关键术语\n"
            "2. 重要的方法、步骤和技巧\n"
            "3. 实际案例和应用场景\n"
            "4. 最佳实践和注意事项\n"
            "5. 相关工具和资源推荐\n"
            "6. 技术规范和标准\n"
            "7. 常见问题和解决方案\n"
            "8. 行业趋势和发展方向\n\n"
            "请用专业但易懂的语言总结内容，突出核心知识点和实用价值。"
        )
    
    # 从环境变量或参数获取提示词类型
    if not prompt_type:
        prompt_type = os.getenv("SYSTEM_PROMPT_TYPE", prompts_config.get("default_prompt_type", "general"))
    
    # 获取指定类型的提示词
    prompts = prompts_config.get("prompts", {})
    if prompt_type in prompts:
        return prompts[prompt_type]["system_prompt"]
    else:
        logger.warning(f"未找到提示词类型 '{prompt_type}'，使用默认类型")
        default_type = prompts_config.get("default_prompt_type", "general")
        if default_type in prompts:
            return prompts[default_type]["system_prompt"]
        else:
            # 如果默认类型也不存在，返回第一个可用的提示词
            if prompts:
                first_key = list(prompts.keys())[0]
                return prompts[first_key]["system_prompt"]
            else:
                # 如果配置文件中没有任何提示词，返回硬编码的默认提示词
                return get_system_prompt()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BASE_URL = os.getenv("BASE_URL")
MODEL = os.getenv("MODEL")

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")  # SerpAPI的API密钥

# Tor代理配置
USE_TOR = os.getenv("USE_TOR", "false").lower() == "true"
TOR_SOCKS_PORT = int(os.getenv("TOR_SOCKS_PORT", "9050"))
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
TOR_PASSWORD = os.getenv("TOR_PASSWORD", "")
TOR_EXECUTABLE_PATH = os.getenv("TOR_EXECUTABLE_PATH", "tor")  # Tor可执行文件路径

# 全局自定义headers和可选Cookie
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.zhihu.com/",
    "Connection": "keep-alive",
}
DEFAULT_COOKIES = os.getenv("SCRAPER_COOKIES", "")  # 可在.env中配置Cookie字符串

def parse_cookies(cookie_str):
    cookies = {}
    for item in cookie_str.split(';'):
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies


class TorManager:
    """Tor代理管理器（使用subprocess自动启动）"""
    
    def __init__(self):
        self.tor_process = None
        self.is_running = False
        self.lock = threading.Lock()
        self.log_file = None
    
    def start_tor(self):
        """使用subprocess启动Tor进程"""
        if self.is_running:
            return True
            
        try:
            with self.lock:
                if self.is_running:
                    return True
                
                # 检查是否已有外部Tor进程在运行
                if self._check_existing_tor():
                    logger.info("Detected existing Tor process, using it")
                    self.is_running = True
                    return True
                    
                # Starting Tor process...
                
                # 检查Tor可执行文件是否存在
                tor_cmd = TOR_EXECUTABLE_PATH
                if not self._check_tor_executable(tor_cmd):
                    # ERROR: Tor executable not found
                    return False
                
                # 构建Tor启动命令
                # 首先检查是否有配置文件
                torrc_path = "./torrc"
                if os.path.exists(torrc_path):
                    cmd = [tor_cmd, "-f", torrc_path]
                    # 如果设置了密码，添加密码配置
                    if TOR_PASSWORD:
                        cmd.extend(["--HashedControlPassword", self._hash_password(TOR_PASSWORD)])
                else:
                    # 使用命令行参数
                    cmd = [
                        tor_cmd,
                        "--SocksPort", str(TOR_SOCKS_PORT),
                        "--ControlPort", str(TOR_CONTROL_PORT),
                        "--DataDirectory", "./tor_data",
                        "--Log", "notice file ./tor_data/tor.log",
                        "--NumEntryGuards", "8",
                        "--CircuitBuildTimeout", "30",
                        "--MaxClientCircuitsPending", "32"
                    ]
                    
                    # 如果设置了密码，添加密码配置
                    if TOR_PASSWORD:
                        cmd.extend(["--HashedControlPassword", self._hash_password(TOR_PASSWORD)])
                
                # 确保数据目录存在
                data_dir = "./tor_data"
                if not os.path.exists(data_dir):
                    os.makedirs(data_dir)
                
                # 启动Tor进程，重定向输出到文件避免编码问题
                log_file_path = os.path.join(data_dir, 'tor.log')
                try:
                    log_file = open(log_file_path, 'w', encoding='utf-8', errors='ignore')
                    
                    # 记录启动命令用于调试
                    logger.info(f"Starting Tor with command: {' '.join(cmd)}")
                    
                    self.tor_process = subprocess.Popen(
                        cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                    )
                    self.log_file = log_file
                    
                    # 检查进程是否立即退出
                    time.sleep(2)
                    if self.tor_process.poll() is not None:
                        # 进程已退出，读取日志查看错误
                        log_file.close()
                        try:
                            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                log_content = f.read()
                                logger.error(f"Tor process exited with code {self.tor_process.returncode}")
                                logger.error(f"Log content: {log_content[:500]}")
                        except:
                            pass
                        return False
                    
                    # 等待Tor启动
                    if self._wait_for_tor_ready():
                        self.is_running = True
                        # SUCCESS: Tor started, SOCKS proxy port ready
                        return True
                    else:
                        # ERROR: Tor startup timeout
                        self.cleanup()
                        return False
                        
                except Exception as e:
                    logger.error(f"Failed to start Tor process: {e}")
                    if 'log_file' in locals():
                        try:
                            log_file.close()
                        except:
                            pass
                    return False
                    
        except Exception as e:
            # ERROR: Failed to start Tor
            self.cleanup()
            return False
    
    def _check_tor_executable(self, tor_cmd):
        """检查Tor可执行文件是否存在"""
        try:
            result = subprocess.run([tor_cmd, "--version"], 
                                  capture_output=True, 
                                  timeout=5,
                                  creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            return result.returncode == 0
        except:
            return False
    
    def _check_existing_tor(self):
        """检查是否已有Tor进程在运行"""
        import socket
        try:
            # 检查SOCKS端口是否可用
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', TOR_SOCKS_PORT))
            sock.close()
            
            if result == 0:
                # SOCKS端口可用，再检查控制端口
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex(('127.0.0.1', TOR_CONTROL_PORT))
                    sock.close()
                    
                    if result == 0:
                        # 两个端口都可用，说明有Tor在运行
                        return True
                except:
                    pass
        except:
            pass
        
        return False
    
    def _hash_password(self, password):
        """生成Tor密码哈希（简化版）"""
        try:
            import hashlib
            import base64
            salt = os.urandom(8)
            key = hashlib.pbkdf2_hmac('sha1', password.encode(), salt, 1000, 20)
            return base64.b64encode(salt + key).decode()
        except:
            return None
    
    def _wait_for_tor_ready(self, timeout=30):
        """等待Tor准备就绪（简化版本，只检查端口可用性）"""
        import socket
        start_time = time.time()
        
        # 等待SOCKS端口可用
        while time.time() - start_time < timeout:
            try:
                # 尝试连接SOCKS端口
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('127.0.0.1', TOR_SOCKS_PORT))
                sock.close()
                
                if result == 0:
                    # SOCKS端口可用，再检查控制端口
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex(('127.0.0.1', TOR_CONTROL_PORT))
                        sock.close()
                        
                        if result == 0:
                            # 两个端口都可用，认为Tor已准备就绪
                            logger.info("Tor ports are ready")
                            return True
                    except:
                        pass
                    
            except:
                pass
                
            time.sleep(1)
            
        logger.warning(f"Tor startup timeout after {timeout} seconds")
        return False
    
    def new_identity(self):
        """请求新的Tor身份（通过重启实现）"""
        if not self.is_running:
            return False
            
        try:
            # Changing Tor identity...
            self.cleanup()
            time.sleep(2)
            return self.start_tor()
        except Exception as e:
            # Failed to change Tor identity
            return False
    
    def get_proxy_config(self):
        """获取代理配置"""
        if not self.is_running:
            return None
        return f"socks5://127.0.0.1:{TOR_SOCKS_PORT}"
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.tor_process:
                self.tor_process.terminate()
                try:
                    self.tor_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.tor_process.kill()
                self.tor_process = None
                
            self.is_running = False
            
            # 关闭日志文件
            if hasattr(self, 'log_file') and self.log_file:
                try:
                    self.log_file.close()
                    self.log_file = None
                except Exception as e:
                    # Error closing log file
                    pass
                    
            # Tor process stopped
        except Exception as e:
            # Error cleaning up Tor resources
            pass


# 全局Tor管理器实例
tor_manager = TorManager() if USE_TOR else None


def get_http_client_config():
    """获取HTTP客户端配置"""
    config = {
        "timeout": 120.0,
        "follow_redirects": True,
    }
    
    if USE_TOR and tor_manager and tor_manager.is_running and SOCKS_AVAILABLE:
        proxy_url = tor_manager.get_proxy_config()
        if proxy_url:
            try:
                # 使用httpx-socks的AsyncProxyTransport来支持SOCKS5代理
                transport = AsyncProxyTransport.from_url(proxy_url)
                config["transport"] = transport
                logger.info(f"使用Tor代理 (transport): {proxy_url}")
            except Exception as e:
                logger.warning(f"代理配置错误: {e}")
                logger.info("将使用普通网络连接")
    elif USE_TOR and tor_manager and tor_manager.is_running and not SOCKS_AVAILABLE:
        logger.warning("检测到Tor代理已启用，但httpx-socks未安装，无法使用SOCKS代理")
        logger.info("请运行: pip install httpx-socks[asyncio]")
    
    return config


# 导入crawler_framework
# 导入爬虫框架（在日志配置之后）
from utils.crawler_framework import CrawlerFramework

# 初始化爬虫框架（只使用Google搜索引擎）
crawler = CrawlerFramework()

# 设置默认只使用Google搜索引擎
default_search_engine = "google"

# 获取当前模块的 logger
logger = logging.getLogger(__name__)

def search_web(keyword: str, max_results=12):
    """使用Google搜索引擎搜索网页 - 兼容性保留函数"""
    logger.info("注意: search_web函数已经过时，建议使用新的通用爬虫框架 crawler.search_and_parse")
    try:
        # 使用新框架的Google搜索（只使用Google引擎）
        result = crawler.search_and_parse(default_search_engine, keyword, max_results)
        
        if result["parsed_response"]["success"]:
            # 返回URL列表以保持向后兼容
            urls = [item["url"] for item in result["parsed_response"]["results"] if "url" in item]
            return urls
        else:
            logger.error(f"搜索失败: {result['parsed_response'].get('error', '未知错误')}")
            return []
            
    except Exception as e:
        logger.error(f"搜索失败: {str(e)}")
        return []

@mcp.tool()
def fetch_raw_data(keyword: str, engine: str = None, max_results: int = 10) -> str:
    """
    从指定搜索引擎获取原始数据
    
    Args:
        engine: 搜索引擎名称 (google, bing, baidu, duckduckgo)
        keyword: 搜索关键词
        max_results: 最大结果数
    
    Returns:
        包含原始数据、元数据和调试信息的JSON字符串
    """
    try:
        # 如果未指定搜索引擎，使用默认的Google
        if engine is None:
            engine = default_search_engine
            
        result = crawler.fetch_raw_data(engine, keyword, max_results)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "engine": engine,
            "keyword": keyword
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def parse_search_results(raw_response_json: str, engine: str = None, custom_rules: str = None) -> str:
    """
    根据配置规则解析原始搜索数据
    
    Args:
        raw_response_json: fetch_raw_data返回的JSON字符串
        engine: 搜索引擎名称（可选，如果raw_response中有）
        custom_rules: 自定义解析规则的JSON字符串（可选）
    
    Returns:
        解析后的结构化数据JSON字符串
    """
    try:
        # 解析输入参数
        raw_response = json.loads(raw_response_json)
        custom_rules_dict = json.loads(custom_rules) if custom_rules else None
        
        # 执行解析
        result = crawler.parse_results(raw_response, engine, custom_rules_dict)
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"JSON解析失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
async def search_and_parse_universal(keyword: str, engine: str = None, max_results: int = 10, 
                                   custom_rules: str = None, extract_content: bool = True,
                                   requirement_type: str = "", target_conversion_type: str = "",
                                   auto_save: bool = True, use_ai: bool = False, prompt_type: str = None) -> str:
    """
    通用搜索和解析工具 - 一站式搜索、解析和内容提取
    
    Args:
        engine: 搜索引擎名称 (google, bing, baidu, duckduckgo)
        keyword: 搜索关键词
        max_results: 最大结果数
        custom_rules: 自定义解析规则的JSON字符串（可选）
        extract_content: 是否对搜索结果中的URL进行内容抓取和知识提取
        requirement_type: 需求类型（如：自然语言需求、用户故事等）
        target_conversion_type: 目标转换类型（如：数据流图、用例图等）
        auto_save: 是否自动保存提取的知识库到文件
        use_ai: 是否启用AI增强的知识提取
        prompt_type: 指定AI系统提示词类型（默认根据requirement_type推断）
        
    Returns:
        包含搜索结果、解析数据和知识提取结果的完整响应JSON字符串
    """
    try:
        # 如果未指定搜索引擎，使用默认的Google
        if engine is None:
            engine = default_search_engine
            
        # 解析自定义规则
        custom_rules_dict = json.loads(custom_rules) if custom_rules else None
        
        # 执行搜索和解析
        search_result = crawler.search_and_parse(engine, keyword, max_results, custom_rules_dict)
        
        # 如果不需要内容提取，直接返回搜索结果
        if not extract_content:
            return json.dumps(search_result, ensure_ascii=False, indent=2)
        
        # 对搜索结果中的URL进行内容抓取和知识提取
        extracted_knowledge = []
        failed_extractions = []
        
        # 从解析结果中获取URL列表
        parsed_response = search_result.get("parsed_response", {})
        if parsed_response.get("success") and "results" in parsed_response:
            urls_to_extract = []
            for result in parsed_response["results"][:max_results]:
                if "url" in result:
                    urls_to_extract.append({
                        "url": result["url"],
                        "title": result.get("title", ""),
                        "snippet": result.get("snippet", "")
                    })
            
            # 对每个URL进行内容抓取和知识提取
            for url_info in urls_to_extract:
                try:
                    url = url_info["url"]
                    
                    # 抓取网页内容
                    scrape_result = await scrape_webpage(url)
                    
                    if scrape_result.startswith("[ERROR]"):
                        failed_extractions.append({
                            "url": url,
                            "error": f"网页抓取失败: {scrape_result}"
                        })
                        continue
                    
                    # 提取网页内容和标题
                    content = scrape_result
                    title = url_info["title"]
                    
                    # 尝试从内容中提取标题（查找【标题】标记）
                    if "【标题】" in content:
                        title_start = content.find("【标题]") + 4 if "【标题】" in content else -1
                        if title_start != -1:
                            title_end = content.find("\n", title_start)
                            if title_end > title_start:
                                extracted_title = content[title_start:title_end].strip()
                                if extracted_title:
                                    title = extracted_title
                    
                    if not title:
                        title = f"从{url}提取的内容"
                    
                    # 根据配置决定是否使用AI提取
                    extraction_method = "rules"
                    knowledge_base = None
                    
                    if use_ai:
                        try:
                            # 推断提示词类型
                            ai_prompt_type = prompt_type or requirement_type or "requirement_analysis"
                            ai_json = extract_knowledge_with_ai(
                                content=content,
                                url=url,
                                title=title,
                                requirement_type=requirement_type,
                                target_conversion_type=target_conversion_type,
                                prompt_type=ai_prompt_type
                            )
                            ai_res = json.loads(ai_json) if isinstance(ai_json, str) else ai_json
                            if ai_res.get("success"):
                                knowledge_base = ai_res.get("knowledge_base")
                                extraction_method = "ai"
                            else:
                                # 回退到规则提取
                                knowledge_base = universal_processor.extract_knowledge(
                                    content=content,
                                    url=url,
                                    title=title,
                                    requirement_type=requirement_type,
                                    target_conversion_type=target_conversion_type
                                )
                                extraction_method = "rules_fallback"
                        except Exception:
                            # AI调用失败，回退到规则提取
                            knowledge_base = universal_processor.extract_knowledge(
                                content=content,
                                url=url,
                                title=title,
                                requirement_type=requirement_type,
                                target_conversion_type=target_conversion_type
                            )
                            extraction_method = "rules_error_fallback"
                    else:
                        # 仅规则提取
                        knowledge_base = universal_processor.extract_knowledge(
                            content=content,
                            url=url,
                            title=title,
                            requirement_type=requirement_type,
                            target_conversion_type=target_conversion_type
                        )
                        extraction_method = "rules"
                    
                    extraction_result = {
                        "url": url,
                        "title": title,
                        "snippet": url_info["snippet"],
                        "knowledge_base": knowledge_base,
                        "extraction_success": True,
                        "extraction_method": extraction_method
                    }
                    
                    # 如果启用自动保存，保存知识库到文件
                    if auto_save:
                        try:
                            filepath = universal_processor.save_knowledge_base(knowledge_base)
                            extraction_result["saved_filepath"] = filepath
                        except Exception as save_error:
                            extraction_result["save_warning"] = f"保存失败: {str(save_error)}"
                    
                    extracted_knowledge.append(extraction_result)
                    
                except Exception as e:
                    failed_extractions.append({
                        "url": url_info["url"],
                        "error": f"内容提取失败: {str(e)}"
                    })
        
        # 构建完整的响应
        final_result = {
            "search_result": search_result,
            "content_extraction": {
                "success": True,
                "total_urls_processed": len(extracted_knowledge) + len(failed_extractions),
                "successful_extractions": len(extracted_knowledge),
                "failed_extractions": len(failed_extractions),
                "extracted_knowledge": extracted_knowledge,
                "failed_urls": failed_extractions
            },
            "summary": {
                "engine": engine,
                "keyword": keyword,
                "search_success": search_result.get("parsed_response", {}).get("success", False),
                "extraction_enabled": extract_content,
                "total_knowledge_bases": len(extracted_knowledge),
                "ai_mode": use_ai,
                "prompt_type": prompt_type or requirement_type or "requirement_analysis"
            }
        }
        
        return json.dumps(final_result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"自定义规则JSON解析失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "engine": engine,
            "keyword": keyword
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def get_available_search_engines() -> str:
    """
    获取可用的搜索引擎列表及其配置信息
    
    Returns:
        搜索引擎信息的JSON字符串
    """
    try:
        engines = crawler.get_available_engines()
        engine_details = {}
        
        for engine in engines:
            config = crawler.get_engine_info(engine)
            engine_details[engine] = {
                "api_name": config.get("api_name", "未知"),
                "supported_parameters": config.get("parameters", {}).get("optional", []),
                "primary_keys": config.get("parsing_rules", {}).get("primary_keys", [])
            }
        
        result = {
            "available_engines": engines,
            "engine_details": engine_details,
            "total_engines": len(engines)
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def configure_search_engine(engine: str, config_json: str) -> str:
    """
    动态配置搜索引擎解析规则（运行时配置）
    
    Args:
        engine: 搜索引擎名称
        config_json: 配置规则的JSON字符串
        
    Returns:
        配置结果的JSON字符串
    """
    try:
        config = json.loads(config_json)
        
        # 验证配置格式
        required_fields = ["engine", "parsing_rules"]
        for field in required_fields:
            if field not in config:
                return json.dumps({
                    "success": False,
                    "error": f"配置缺少必需字段: {field}"
                }, ensure_ascii=False, indent=2)
        
        # 更新运行时配置
        crawler.engine_configs[engine] = config
        
        result = {
            "success": True,
            "engine": engine,
            "message": f"搜索引擎 {engine} 配置已更新",
            "config_summary": {
                "primary_keys": config.get("parsing_rules", {}).get("primary_keys", []),
                "link_fields": config.get("parsing_rules", {}).get("link_fields", []),
                "api_name": config.get("api_name", "未指定")
            }
        }
        
        return json.dumps(result, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        error_result = {
            "success": False,
            "error": f"配置JSON解析失败: {str(e)}"
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
async def check_tor_ip() -> str:
    """Check current IP address through Tor proxy"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    try:
        # Check IP through Tor proxy
        config = get_http_client_config()
        async with httpx.AsyncClient(**config) as client:
            response = await client.get("https://httpbin.org/ip", timeout=10)
            if response.status_code == 200:
                ip_data = response.json()
                tor_ip = ip_data.get('origin', 'Unknown')
                
                # Also check without proxy for comparison
                async with httpx.AsyncClient() as normal_client:
                    normal_response = await normal_client.get("https://httpbin.org/ip", timeout=10)
                    if normal_response.status_code == 200:
                        normal_ip_data = normal_response.json()
                        normal_ip = normal_ip_data.get('origin', 'Unknown')
                        
                        return f"[SUCCESS] IP check completed\nTor IP: {tor_ip}\nNormal IP: {normal_ip}\nProxy working: {'Yes' if tor_ip != normal_ip else 'No'}"
                    else:
                        return f"[SUCCESS] Tor IP: {tor_ip}\n[WARNING] Could not get normal IP for comparison"
            else:
                return f"[ERROR] Failed to check IP through Tor. Status code: {response.status_code}"
                
    except Exception as e:
        return f"[ERROR] Failed to check Tor IP: {str(e)}"


@mcp.tool()
async def test_tor_connection() -> str:
    """Test Tor proxy connection with multiple endpoints"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    test_urls = [
        "https://httpbin.org/ip",
        "https://check.torproject.org/api/ip",
        "https://icanhazip.com"
    ]
    
    results = []
    config = get_http_client_config()
    
    async with httpx.AsyncClient(**config) as client:
        for url in test_urls:
            try:
                start_time = time.time()
                response = await client.get(url, timeout=15)
                end_time = time.time()
                
                if response.status_code == 200:
                    response_time = round((end_time - start_time) * 1000, 2)
                    results.append(f"✓ {url}: OK ({response_time}ms)")
                else:
                    results.append(f"✗ {url}: HTTP {response.status_code}")
                    
            except Exception as e:
                results.append(f"✗ {url}: {str(e)}")
    
    success_count = len([r for r in results if r.startswith('✓')])
    total_count = len(results)
    
    status = "[SUCCESS]" if success_count == total_count else "[PARTIAL]" if success_count > 0 else "[ERROR]"
    
    return f"{status} Tor connection test completed ({success_count}/{total_count} passed)\n" + "\n".join(results)


@mcp.tool()
def search_knowledge(query: str, intent: str = None, top_k: int = 5, smart_search: bool = None) -> str:
    """
    Search the Software Engineering Knowledge Base (SE-KB) for relevant information.
    
    Args:
        query: The natural language query (e.g., "how to handle user login in DFD")
        intent: Optional search intent filter. Allowed values:
            - "concept": Definitions of terms (e.g., "what is a process")
            - "rule": Validation rules and constraints (e.g., "naming conventions")
            - "example": Practical examples and patterns
            - "template": Standard templates
            - "theory": Theoretical background
            If not provided, the system will automatically detect the intent.
        top_k: Number of results to return (default: 5)
        smart_search: Whether to use advanced query decomposition for complex queries.
                      If None (default), it automatically enables for long queries (>20 chars) without explicit intent.
        
    Returns:
        JSON string containing the search results with scores and metadata.
    """
    if not knowledge_retriever:
        return json.dumps({
            "error": "KnowledgeRetriever is not initialized. Please check server logs."
        }, ensure_ascii=False)
        
    try:
        # Determine whether to use smart search
        use_smart_search = smart_search
        if use_smart_search is None:
            use_smart_search = (not intent) and (len(query) > 20)

        if use_smart_search and query_planner:
            logger.info(f"Using QueryPlanner for query: {query[:50]}...")
            plan_result = query_planner.search(query, top_k)
            
            results = []
            for r in plan_result.merged_results:
                results.append({
                    "content": r["content"],
                    "score": r["score"],
                    "source": r.get("source", "unknown"),
                    "type": r.get("type", "unknown"),
                    "collection": r["collection"],
                    "matched_queries": r.get("matched_queries", [])
                })
                
            return json.dumps({
                "query": plan_result.original_query,
                "intent": "decomposed_search",
                "sub_queries": [
                    {"query": sq.query, "intent": sq.intent} for sq in plan_result.sub_queries
                ],
                "total_found": len(results),
                "results": results
            }, ensure_ascii=False, indent=2)

        # Map string intent to Enum
        query_intent = None
        if intent:
            try:
                query_intent = QueryIntent(intent.lower())
            except ValueError:
                pass  # Use auto-detection if invalid intent provided
        
        # Execute retrieval
        response = knowledge_retriever.retrieve(
            query=query,
            top_k=top_k,
            intent=query_intent
        )
        
        # Format results
        results = []
        for r in response.results:
            results.append({
                "content": r.text,
                "score": round(r.score, 4),
                "source": r.metadata.get("source", "unknown"),
                "type": r.metadata.get("type", "unknown"),
                "collection": r.collection
            })
            
        return json.dumps({
            "query": response.query,
            "detected_intent": response.intent.value,
            "total_found": response.total_found,
            "results": results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Search knowledge failed: {e}")
        return json.dumps({
            "error": f"Search failed: {str(e)}"
        }, ensure_ascii=False)

@mcp.tool()
def get_dfd_generation_context(requirement: str) -> str:
    """
    Get a complete context package for generating DFDs based on requirements.
    This tool is designed for the "Requirement-to-DFD" generation system.
    It automatically decomposes the requirement into sub-queries to retrieve
    comprehensive knowledge about concepts, rules, and patterns relevant to the specific domain.
    
    Args:
        requirement: The text description of the system requirements.
        
    Returns:
        A JSON string containing:
        - decomposed_queries: List of sub-queries generated
        - concepts: Relevant DFD concepts found
        - rules: Relevant validation rules found
        - patterns: Similar design patterns found
        - examples: Relevant examples found
    """
    if not query_planner:
        return json.dumps({
            "error": "QueryPlanner is not initialized."
        }, ensure_ascii=False)

    try:
        # 使用 QueryPlanner 进行全量搜索
        # 这里我们希望获得比较全面的结果，所以 top_k 稍微大一点
        plan_result = query_planner.search(requirement, top_k=8)
        
        # 将结果按类型分类整理
        categorized_results = {
            "concepts": [],
            "rules": [],
            "patterns": [],
            "examples": [],
            "others": []
        }
        
        for r in plan_result.merged_results:
            # 简化结果对象
            item = {
                "content": r["content"],
                "score": r["score"],
                "source": r.get("source"),
                "matched_queries": r.get("matched_queries", [])
            }
            
            # 根据 collection 或 type 分类
            coll = r["collection"]
            if "concept" in coll:
                categorized_results["concepts"].append(item)
            elif "rule" in coll or "level" in coll:
                categorized_results["rules"].append(item)
            elif "template" in coll or "pattern" in coll:
                categorized_results["patterns"].append(item)
            elif "example" in coll:
                categorized_results["examples"].append(item)
            else:
                categorized_results["others"].append(item)
                
        return json.dumps({
            "original_requirement": requirement,
            "sub_queries": [
                {"query": sq.query, "intent": sq.intent} for sq in plan_result.sub_queries
            ],
            "knowledge_context": categorized_results
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Context generation failed: {e}")
        return json.dumps({
            "error": f"Failed to generate context: {str(e)}"
        }, ensure_ascii=False)
        - related_concepts: Definitions of relevant DFD elements
        - rules: Mandatory validation rules (naming, balance, etc.)
        - examples: Similar system examples found in the knowledge base
        - templates: Recommended templates for the task
    """
    if not knowledge_retriever:
        return json.dumps({"error": "KnowledgeRetriever not initialized"}, ensure_ascii=False)
        
    try:
        context = {
            "requirement": requirement,
            "timestamp": datetime.datetime.now().isoformat(),
            "related_knowledge": {}
        }
        
        # 1. Get relevant concepts (What elements might be used?)
        concepts = knowledge_retriever.retrieve(
            query=requirement, 
            intent=QueryIntent.CONCEPT,
            top_k=3
        )
        context["related_knowledge"]["concepts"] = [
            {"term": r.metadata.get("title", "Unknown"), "def": r.text} 
            for r in concepts.results
        ]
        
        # 2. Get validation rules (What constraints must be met?)
        rules = knowledge_retriever.retrieve(
            query="DFD validation rules naming consistency balance", # Generic query for core rules
            intent=QueryIntent.RULE,
            top_k=5
        )
        context["related_knowledge"]["rules"] = [r.text for r in rules.results]
        
        # 3. Get similar examples (How did others do it?)
        examples = knowledge_retriever.retrieve(
            query=requirement,
            intent=QueryIntent.EXAMPLE,
            top_k=3
        )
        context["related_knowledge"]["examples"] = [
            {"title": r.metadata.get("title", ""), "content": r.text[:500] + "..."} 
            for r in examples.results
        ]
        
        # 4. Get Templates (Structure)
        templates = knowledge_retriever.retrieve(
            query="context diagram level-1 dfd template",
            intent=QueryIntent.TEMPLATE,
            top_k=1
        )
        if templates.results:
            context["related_knowledge"]["recommended_template"] = templates.results[0].text
            
        return json.dumps(context, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Get DFD context failed: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool()
def validate_tor_config() -> str:
    """Validate Tor configuration settings"""
    issues = []
    warnings = []
    
    # Check if Tor is enabled
    if not USE_TOR:
        return "Tor proxy feature is disabled. Set USE_TOR=true in .env to enable."
    
    # Check Tor executable path
    if not TOR_EXECUTABLE_PATH:
        issues.append("TOR_EXECUTABLE_PATH is not set")
    else:
        import os
        if not os.path.exists(TOR_EXECUTABLE_PATH):
            issues.append(f"Tor executable not found at: {TOR_EXECUTABLE_PATH}")
    
    # Check ports
    if TOR_SOCKS_PORT == TOR_CONTROL_PORT:
        issues.append("SOCKS port and Control port cannot be the same")
    
    if TOR_SOCKS_PORT < 1024 or TOR_SOCKS_PORT > 65535:
        issues.append(f"Invalid SOCKS port: {TOR_SOCKS_PORT} (must be 1024-65535)")
    
    if TOR_CONTROL_PORT < 1024 or TOR_CONTROL_PORT > 65535:
        issues.append(f"Invalid Control port: {TOR_CONTROL_PORT} (must be 1024-65535)")
    
    # Check password
    if not TOR_PASSWORD:
        warnings.append("No control password set (recommended for security)")
    
    # Check httpx-socks availability
    if not SOCKS_AVAILABLE:
        issues.append("httpx-socks library not available. Install with: pip install httpx-socks")
    
    # Generate report
    if issues:
        return f"[ERROR] Configuration validation failed:\n" + "\n".join(f"- {issue}" for issue in issues) + \
               (f"\n\nWarnings:\n" + "\n".join(f"- {warning}" for warning in warnings) if warnings else "")
    elif warnings:
        return f"[WARNING] Configuration has warnings:\n" + "\n".join(f"- {warning}" for warning in warnings)
    else:
        return "[SUCCESS] Tor configuration is valid"


@mcp.tool()
def get_tor_bootstrap_status() -> str:
    """Get detailed Tor bootstrap status and progress"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    try:
        import socket
        import re
        
        # Connect to control port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', TOR_CONTROL_PORT))
        
        # Authenticate
        if TOR_PASSWORD:
            auth_cmd = f'AUTHENTICATE "{TOR_PASSWORD}"\r\n'
        else:
            auth_cmd = 'AUTHENTICATE\r\n'
        
        sock.send(auth_cmd.encode())
        response = sock.recv(1024).decode()
        
        if '250 OK' not in response:
            sock.close()
            return "[ERROR] Failed to authenticate with Tor control port"
        
        results = []
        
        # Get bootstrap status
        sock.send(b'GETINFO status/bootstrap-phase\r\n')
        bootstrap_response = sock.recv(1024).decode()
        
        if 'status/bootstrap-phase=' in bootstrap_response:
            # Extract bootstrap info
            lines = bootstrap_response.split('\n')
            for line in lines:
                if 'status/bootstrap-phase=' in line:
                    bootstrap_info = line.split('status/bootstrap-phase=')[1].strip()
                    
                    # Parse progress
                    progress_match = re.search(r'PROGRESS=(\d+)', bootstrap_info)
                    if progress_match:
                        progress = int(progress_match.group(1))
                        results.append(f"Bootstrap Progress: {progress}%")
                        
                        if progress == 100:
                            results.append("Status: ✅ Fully bootstrapped")
                        elif progress >= 80:
                            results.append("Status: 🟡 Nearly ready")
                        else:
                            results.append("Status: 🔄 Still bootstrapping")
                    
                    # Parse summary
                    summary_match = re.search(r'SUMMARY="([^"]+)"', bootstrap_info)
                    if summary_match:
                        summary = summary_match.group(1)
                        results.append(f"Summary: {summary}")
                    
                    break
        
        # Get circuit count
        sock.send(b'GETINFO status/circuit-established\r\n')
        circuit_response = sock.recv(1024).decode()
        
        if 'status/circuit-established=' in circuit_response:
            if 'status/circuit-established=1' in circuit_response:
                results.append("Circuits: ✅ Established")
            else:
                results.append("Circuits: ❌ Not established")
        
        # Get version info
        sock.send(b'GETINFO version\r\n')
        version_response = sock.recv(1024).decode()
        
        if 'version=' in version_response:
            lines = version_response.split('\n')
            for line in lines:
                if 'version=' in line:
                    version = line.split('version=')[1].strip()
                    results.append(f"Tor Version: {version}")
                    break
        
        sock.send(b'QUIT\r\n')
        sock.close()
        
        if results:
            return "[SUCCESS] Tor bootstrap status:\n" + "\n".join(results)
        else:
            return "[WARNING] Could not retrieve bootstrap status"
            
    except Exception as e:
        return f"[ERROR] Failed to get bootstrap status: {str(e)}"


@mcp.tool()
async def auto_rotate_tor_identity(interval_seconds: int = 300, max_rotations: int = 10) -> str:
    """Automatically rotate Tor identity at specified intervals"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    if interval_seconds < 60:
        return "[ERROR] Minimum interval is 60 seconds to avoid overloading Tor network."
    
    if max_rotations < 1 or max_rotations > 100:
        return "[ERROR] Max rotations must be between 1 and 100."
    
    try:
        rotation_count = 0
        results = []
        
        results.append(f"[INFO] Starting automatic Tor identity rotation")
        results.append(f"[INFO] Interval: {interval_seconds} seconds, Max rotations: {max_rotations}")
        
        # Get initial IP
        try:
            config = get_http_client_config()
            async with httpx.AsyncClient(**config) as client:
                response = await client.get("https://httpbin.org/ip", timeout=10)
                if response.status_code == 200:
                    initial_ip = response.json().get('origin', 'Unknown')
                    results.append(f"[INFO] Initial IP: {initial_ip}")
        except:
            results.append(f"[WARNING] Could not get initial IP")
        
        while rotation_count < max_rotations:
            # Wait for the specified interval
            await asyncio.sleep(interval_seconds)
            
            # Rotate identity
            success = tor_manager.new_identity()
            rotation_count += 1
            
            if success:
                # Wait a bit for the new circuit to establish
                await asyncio.sleep(10)
                
                # Check new IP
                try:
                    config = get_http_client_config()
                    async with httpx.AsyncClient(**config) as client:
                        response = await client.get("https://httpbin.org/ip", timeout=10)
                        if response.status_code == 200:
                            new_ip = response.json().get('origin', 'Unknown')
                            results.append(f"[SUCCESS] Rotation {rotation_count}: New IP {new_ip}")
                        else:
                            results.append(f"[WARNING] Rotation {rotation_count}: Could not verify new IP")
                except Exception as e:
                    results.append(f"[WARNING] Rotation {rotation_count}: IP check failed - {str(e)}")
            else:
                results.append(f"[ERROR] Rotation {rotation_count}: Failed to change identity")
        
        results.append(f"[INFO] Automatic rotation completed. Total rotations: {rotation_count}")
        return "\n".join(results)
        
    except Exception as e:
        return f"[ERROR] Auto rotation failed: {str(e)}"


@mcp.tool()
def get_tor_circuit_info() -> str:
    """Get information about current Tor circuit"""
    if not USE_TOR or not tor_manager:
        return "Tor proxy feature is disabled."
    
    if not tor_manager.is_running:
        return "Tor proxy is not running. Please start Tor proxy first."
    
    try:
        import socket
        import struct
        
        # Try to connect to Tor control port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', TOR_CONTROL_PORT))
        
        # Authenticate if password is set
        if TOR_PASSWORD:
            auth_cmd = f'AUTHENTICATE "{TOR_PASSWORD}"\r\n'
        else:
            auth_cmd = 'AUTHENTICATE\r\n'
        
        sock.send(auth_cmd.encode())
        response = sock.recv(1024).decode()
        
        if '250 OK' not in response:
            sock.close()
            return "[ERROR] Failed to authenticate with Tor control port"
        
        # Get circuit information
        sock.send(b'GETINFO circuit-status\r\n')
        circuit_response = sock.recv(4096).decode()
        
        sock.send(b'QUIT\r\n')
        sock.close()
        
        if '250 OK' in circuit_response:
            lines = circuit_response.split('\n')
            circuit_lines = [line for line in lines if line.startswith('250-circuit-status=') or (line.startswith('250+circuit-status='))]
            
            if circuit_lines:
                return f"[SUCCESS] Tor circuit information:\n" + "\n".join(circuit_lines)
            else:
                return "[INFO] No active circuits found"
        else:
            return "[ERROR] Failed to get circuit information"
            
    except Exception as e:
        return f"[ERROR] Failed to get circuit info: {str(e)}"


@mcp.tool()
async def scrape_webpage(url: str, headers=None, cookies=None, prompt_type: str = None) -> str:
    """
    Scrape webpage text + image analysis via vision model + summarize with main model.
    """
    # 检查URL去重
    dedup_instance = get_deduplication_instance()
    is_duplicate, cache_info = dedup_instance.is_url_duplicate(url)
    if is_duplicate:
        return json.dumps({
            "status": "skipped",
            "message": "URL已存在于缓存中，跳过重复抓取",
            "url": url,
            "cached_info": cache_info
        }, ensure_ascii=False, indent=2)
    
    headers = headers or DEFAULT_HEADERS
    # 知乎反爬虫功能已禁用 - 自动判断知乎等站点，自动获取Cookie
    # cookies = cookies or get_cookies_for_url(url) or (parse_cookies(DEFAULT_COOKIES) if DEFAULT_COOKIES else None)
    cookies = cookies or (parse_cookies(DEFAULT_COOKIES) if DEFAULT_COOKIES else None)

    # 支持的图片格式
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.svg']
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

    def normalize_image_url(base_url: str, img_url: str) -> str:
        if img_url.startswith(('http://', 'https://')):
            return img_url
        elif img_url.startswith('//'):
            return 'https:' + img_url
        elif img_url.startswith('/'):
            return urljoin(base_url, img_url)
        else:
            return urljoin(base_url, img_url)

    async def download_image_with_retry(client, img_url: str, max_retries: int = 3) -> bytes:
        for attempt in range(max_retries):
            try:
                response = await client.get(img_url, timeout=10.0)
                if response.status_code != 200:
                    # Image request failed
                    return None
                response.raise_for_status()
                return response.content
            except Exception as e:
                if attempt == max_retries - 1:
                    # Image download failed
                    return None
                await asyncio.sleep(1)

    async def is_valid_image_size(client, img_url: str) -> bool:
        try:
            async with client.stream('GET', img_url) as response:
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > MAX_IMAGE_SIZE:
                    return False
                return True
        except:
            return False

    async def is_valid_image_tag(img_tag) -> bool:
        # 过滤极小图片、icon、广告等
        src = img_tag.get('src', '')
        if not src:
            return False
        # 过滤常见icon/广告关键词
        lower_src = src.lower()
        if any(x in lower_src for x in ['logo', 'icon', 'avatar', 'ad', 'ads', 'spacer', 'blank', 'tracker']):
            return False
        # 过滤极小图片（如宽高<32px）
        try:
            width = int(img_tag.get('width', 0))
            height = int(img_tag.get('height', 0))
            if width and height and (width < 32 or height < 32):
                return False
        except Exception:
            pass
        return True

    async def get_image_description(client, image_data: bytes, max_retries: int = 2) -> str:
        for attempt in range(max_retries):
            try:
                # 处理图片数据
                image = Image.open(BytesIO(image_data)).convert("RGB")
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=85)  # 降低质量以加快传输
                b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                # 调用视觉模型
                visual_payload = {
                    "model": os.getenv("VISUAL_MODEL", "Pro/Qwen/Qwen2.5-VL-7B-Instruct"),
                    "messages": [{"role": "user", "content": "请描述这张图片的内容。"}],
                    "image": b64_img
                }
                
                # 使用硅基流动的API
                VISUAL_API_URL = os.getenv("VISUAL_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
                visual_response = await client.post(
                    VISUAL_API_URL,
                    json=visual_payload,
                    timeout=30.0,  # 增加超时时间
                    headers={
                        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                        "Content-Type": "application/json"
                    }
                )
                try:
                    visual_json = visual_response.json()
                    if isinstance(visual_json, dict):
                        return (
                            visual_json.get("message", {}).get("content") or
                            visual_json.get("choices", [{}])[0].get("message", {}).get("content") or
                            "(视觉模型未返回有效描述)"
                        ).strip()
                    else:
                        return f"(视觉模型返回异常格式: {str(visual_json)})"
                except Exception as json_error:
                    return f"(视觉模型JSON解析失败: {str(json_error)})"
                
            except Exception as e:
                if attempt == max_retries - 1:
                    return f"图片识别失败（{str(e)}）"
                await asyncio.sleep(2)  # 等待2秒后重试

    try:
        # 获取HTTP客户端配置（包含Tor代理设置）
        client_config = get_http_client_config()
        client_config.update({"headers": headers, "cookies": cookies})
        
        async with httpx.AsyncClient(**client_config) as client:
            # Step 1: 抓网页
            response = await client.get(url)
            response.raise_for_status()
            
            # 统一使用UTF-8编码处理，与数据库保持一致的编码（数据库使用utf8mb4，是UTF-8的超集）
            # 这样可以避免编码转换问题，简化处理流程
            response.encoding = "utf-8"  # 强制指定编码为utf-8
            
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                
                for tag in soup(["script", "style"]):
                    tag.decompose()

                # Step 2: 提取全网页正文内容
                title = soup.title.string if soup.title else "无标题"
                headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2'])]
                description = next((m.get("content") for m in soup.find_all("meta", attrs={"name": "description"})), "无描述")
                
                # 提取主要内容
                main_content = []
                for p in soup.find_all(['p', 'div', 'article']):
                    text = p.get_text(strip=True)
                    if text and len(text) > 20:  # 只保留有意义的文本
                        main_content.append(text)

                main_text = f"【标题】{title}\n【描述】{description}\n【结构】{headings}\n\n" + "\n".join(main_content)
            except Exception as e:
                logger.error(f"网页解析失败 {url}: {e}")
                return f"{{\"error\": \"网页解析失败: {str(e)}\", \"url\": \"{url}\"}}"

            # Step 3: 提取图片URL并处理图片
            img_descriptions = []
            image_urls = []
            try:
                img_tags = soup.find_all("img", src=True) if 'soup' in locals() else []
                seen_urls = set()
                valid_imgs = []
                
                # 提取所有有效的图片URL
                logger.info(f"找到 {len(img_tags)} 个img标签")
                for img_tag in img_tags:
                    img_src = img_tag.get("src", "")
                    logger.debug(f"检查图片: {img_src}")
                    if not await is_valid_image_tag(img_tag):
                        logger.debug(f"图片未通过验证: {img_src}")
                        continue
                    img_url = img_tag["src"]
                    img_url = normalize_image_url(url, img_url)
                    if not any(img_url.lower().endswith(ext) for ext in SUPPORTED_IMAGE_FORMATS):
                        logger.debug(f"图片格式不支持: {img_url}")
                        continue
                    if img_url in seen_urls:
                        continue
                    seen_urls.add(img_url)
                    image_urls.append(img_url)  # 保存所有图片URL用于下载
                    valid_imgs.append(img_url)
                    logger.info(f"添加有效图片: {img_url}")
                    if len(valid_imgs) >= 5:  # 只处理前5张用于视觉分析
                        break
                
                logger.info(f"最终提取到 {len(image_urls)} 个图片URL用于下载")
                
                # 对前几张图片进行视觉分析（用于内容理解）
                for i, img_url in enumerate(valid_imgs):
                    try:
                        img_data = await download_image_with_retry(client, img_url)
                        if not img_data:
                            continue  # 跳过无效图片
                        vision_caption = await get_image_description(client, img_data)
                        if vision_caption and not vision_caption.startswith("图片识别失败"):
                            img_descriptions.append(f"第{i+1}张图：{vision_caption}")
                    except Exception as e:
                        logger.warning(f"处理图片 {img_url} 时出错: {str(e)}")
                        continue
            except Exception as e:
                logger.warning(f"图片处理过程出错: {str(e)}")

            # Step 4: 整合图文输入
            all_desc = "\n".join(img_descriptions) if img_descriptions else "未识别出图片内容"

            # 根据是否有图片描述调整提示词
            if img_descriptions:
                final_prompt = (
                    f"请总结这个网页的内容，结合以下文本和图片描述：\n\n"
                    f"📄 文本部分：\n{main_text}\n\n"
                    f"🖼 图片描述：\n{all_desc}"
                )
            else:
                final_prompt = (
                    f"请总结这个网页的内容：\n\n"
                    f"📄 文本内容：\n{main_text}"
                )

            # Step 5: 主模型生成总结
            # 从配置文件获取系统提示词
            system_prompt = get_system_prompt(prompt_type)
            
            final_response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": final_prompt}
                ]
            )

            # 新增：使用新的存储模块保存网页内容和图片
            # ============= 新增本地存储 =============
            import json as _json
            from datetime import datetime as _dt

            # 1. 生成 tech_topic（用标题或首个 heading，去除特殊字符）
            def clean_filename(s):
                return re.sub(r'[^\w\u4e00-\u9fa5]+', '_', s).strip('_')
            tech_topic = title or (headings[0] if headings else "网页内容")
            tech_topic_clean = clean_filename(tech_topic)
            # 2. 时间戳
            crawl_time = _dt.now().strftime('%Y-%m-%dT%H-%M-%S')
            crawl_time_human = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 获取存储实例并保存网页内容（包括图片下载）
            from utils.webpage_storage import get_storage_instance
            storage = get_storage_instance()
            
            # 先准备基本内容用于存储
            basic_content = {
                "title": title,
                "url": url,
                "main_text": main_text,
                "headings": headings,
                "img_descriptions": img_descriptions,
                "crawl_time": crawl_time_human
            }
            # 5. 组装内容（知识库对接格式）
            # 根据网页内容分析DFD相关元素
            try:
                if hasattr(final_response, 'choices') and final_response.choices:
                    content_analysis = final_response.choices[0].message.content or ""
                elif isinstance(final_response, str):
                    content_analysis = final_response
                else:
                    content_analysis = str(final_response)
            except Exception as e:
                content_analysis = f"[ERROR] 内容分析失败: {str(e)}"
                logger.error(f"处理final_response时出错: {e}, final_response类型: {type(final_response)}")
            
            # 使用配置化的格式处理器构建知识库数据
            # 使用当前默认格式类型（可配置）
            format_type = "dfd"  # 可以从环境变量或参数获取
            
            # 根据配置提取知识库数据
            extracted_data = format_processor.extract_knowledge(
                content_analysis, url, title
            )
            
            # 准备元数据
            metadata = {
                "source_url": url,
                "title": title,
                "crawl_time": crawl_time,
                "crawl_time_human": crawl_time_human,
                "extraction_method": "基于配置文件的自动提取",
                "topic": tech_topic
            }
            
            # 生成JSON结构
            json_obj = format_processor.generate_json_structure(
                extracted_data, url, title
            )
            
            # 为了兼容性，提取各个组件的统计信息
            dfd_concepts = extracted_data.get('dfd_concepts', [])
            dfd_rules = extracted_data.get('dfd_rules', [])
            dfd_patterns = extracted_data.get('dfd_patterns', [])
            dfd_cases = extracted_data.get('dfd_cases', [])
            dfd_nlp_mappings = extracted_data.get('dfd_nlp_mappings', [])
            
            # 确保统计信息正确
            if "statistics" not in json_obj:
                json_obj["statistics"] = {
                    "concepts_count": len(dfd_concepts),
                    "rules_count": len(dfd_rules),
                    "patterns_count": len(dfd_patterns),
                    "cases_count": len(dfd_cases),
                    "nlp_mappings_count": len(dfd_nlp_mappings)
                }
            
            # 使用FormatProcessor生成Markdown内容
            markdown_content = format_processor.generate_markdown(
                extracted_data,
                {
                    'title': tech_topic,
                    'source_url': url,
                    'source_title': title,
                    'crawl_time': crawl_time_human,
                    'content_analysis': content_analysis
                }
            )
            md_lines = markdown_content.split('\n')
            # 使用新存储模块保存网页内容和图片
            saved_info = None
            try:
                saved_info = await storage.save_webpage(
                    url=url,
                    html_content=response.text,  # 使用原始HTML内容
                    title=title,
                    metadata=json_obj,  # 将JSON对象作为元数据
                    image_urls=image_urls,
                    client=client  # 传递HTTP客户端用于下载图片
                )
                
                # 记录保存信息
                if saved_info and saved_info.get('success'):
                    logger.info(f"网页内容已保存到: {saved_info['folder_path']}")
                    logger.info(f"下载的图片: {saved_info['images_downloaded']}/{saved_info['total_images']}张")
                else:
                    logger.error(f"保存失败: {saved_info.get('error', '未知错误') if saved_info else '保存信息为空'}")
                
            except Exception as e:
                logger.error(f"使用新存储模块保存失败: {str(e)}，回退到原有方式")
                saved_info = None
            
            # 同时保存到原有的目录结构（为了兼容性）
            json_dir = Path(JSON_LLM_READY_DIR)
            md_dir = Path(MARKDOWN_LLM_READY_DIR)
            json_dir.mkdir(parents=True, exist_ok=True)
            md_dir.mkdir(parents=True, exist_ok=True)
            
            legacy_json_path = json_dir / f"{tech_topic_clean}_{crawl_time}.json"
            legacy_md_path = md_dir / f"{tech_topic_clean}_{crawl_time}.md"
            
            with open(legacy_json_path, 'w', encoding='utf-8') as f:
                _json.dump(json_obj, f, ensure_ascii=False, indent=2)
            with open(legacy_md_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))
            
            # 自动保存到知识库结构化文件
            try:
                kb_result = await save_to_knowledge_base(_json.dumps(json_obj), tech_topic_clean)
                # Knowledge base save result logged
            except Exception as e:
                # Knowledge base save failed, error logged
                pass
            
            # ============= 新增本地存储 END =============
            
            # 返回增强的结果，包含知识库统计信息
            try:
                # 尝试解析响应内容
                if hasattr(final_response, 'choices') and final_response.choices:
                    result_summary = final_response.choices[0].message.content or "[ERROR] 理解失败"
                elif isinstance(final_response, str):
                    result_summary = final_response
                else:
                    result_summary = str(final_response)
            except Exception as e:
                result_summary = f"[ERROR] 响应解析失败: {str(e)}"
            
            # 添加知识库提取统计和存储信息
            try:
                # 尝试获取存储信息
                if saved_info is not None and saved_info.get('success'):
                    storage_stats = f"\n\n🗂️ **新存储结构**:\n" \
                                  f"- 网页文件夹: {saved_info['folder_path']}\n" \
                                  f"- HTML文件: {saved_info['html_file']}\n" \
                                  f"- 元数据文件: {saved_info['metadata_file']}\n"
                    if saved_info['images_downloaded'] > 0:
                        storage_stats += f"- 下载的图片: {saved_info['images_downloaded']}/{saved_info['total_images']}张\n"
                else:
                    storage_stats = "\n\n🗂️ **存储信息**: 使用传统存储方式\n"
            except Exception as e:
                storage_stats = f"\n\n🗂️ **存储信息**: 存储信息获取失败 - {str(e)}\n"
                
            kb_stats = f"\n\n📊 **知识库提取统计**:\n" \
                      f"- 概念定义: {len(dfd_concepts)} 个\n" \
                      f"- 规则条目: {len(dfd_rules)} 个\n" \
                      f"- 模式模板: {len(dfd_patterns)} 个\n" \
                      f"- 案例示例: {len(dfd_cases)} 个\n" \
                      f"- NLP映射: {len(dfd_nlp_mappings)} 个\n" + \
                      storage_stats + \
                      f"\n📁 **兼容性文件位置**:\n" \
                      f"- JSON数据: {legacy_json_path}\n" \
                      f"- Markdown报告: {legacy_md_path}\n" \
                      f"- 知识库文件: {KNOWLEDGE_BASE_DIR.name}/{tech_topic_clean}_*.json"
            
            # 缓存URL和内容
            try:
                dedup_instance.add_url_cache(url, title)
                if dedup_instance.is_content_duplicate(result_summary):
                    # 内容重复但URL不同，记录日志
                    logger.info(f"检测到内容重复但URL不同: {url}")
                else:
                    dedup_instance.add_content_cache(result_summary, title, url)
            except Exception as cache_error:
                logger.warning(f"缓存失败: {str(cache_error)}")
            
            return result_summary + kb_stats

    except Exception as e:
        # 检查是否为代理相关错误，如果是则尝试使用直接爬取模式
        error_str = str(e).lower()
        proxy_errors = ['proxy', 'socks', 'timeout', 'connection', 'network', 'unreachable']
        
        if any(error_keyword in error_str for error_keyword in proxy_errors):
            logger.warning(f"检测到代理相关错误: {str(e)}，尝试使用直接爬取模式")
            try:
                # 使用crawl_webpage_direct作为回退方案
                fallback_result = await crawl_webpage_direct(url, save_content=True)
                return f"⚠️ 代理连接失败，已自动切换到直接爬取模式\n\n{fallback_result}"
            except Exception as fallback_error:
                return f"[ERROR] 代理爬取失败: {str(e)}\n[ERROR] 直接爬取也失败: {str(fallback_error)}"
        else:
            return f"[ERROR] 图文提取失败 {str(e)}"

@mcp.tool()
async def crawl_webpage_direct(url: str, save_content: bool = True) -> str:
    """
    直接爬取网页内容，不使用代理，专门用于解决代理连接超时问题。
    适用于CSDN等网站的内容抓取。
    
    Args:
        url: 要爬取的网页URL
        save_content: 是否保存爬取的内容到本地文件
    
    Returns:
        JSON格式的爬取结果，包含标题、内容、作者、发布时间等信息
    """
    try:
        # 导入WebpageCrawler
        from utils.webpage_crawler import WebpageCrawler
        
        # 创建爬虫实例
        crawler = WebpageCrawler()
        
        # 爬取网页内容
        result = crawler.crawl_and_parse(url, save_data=save_content)
        
        if result['success']:
            # 从解析数据中提取信息
            parsed_data = result.get('parsed_data', {})
            raw_data = result.get('raw_data', {})
            
            # 格式化返回结果
            formatted_result = {
                "status": "success",
                "url": url,
                "title": parsed_data.get('title', ''),
                "author": parsed_data.get('author', ''),
                "publish_time": parsed_data.get('publish_time', ''),
                "word_count": parsed_data.get('word_count', 0),
                "tags": parsed_data.get('tags', []),
                "content_preview": parsed_data.get('content', '')[:500] + '...' if len(parsed_data.get('content', '')) > 500 else parsed_data.get('content', ''),
                "full_content_length": len(parsed_data.get('content', '')),
                "crawl_time": parsed_data.get('parsed_at', ''),
                "raw_data_size": len(raw_data.get('content', ''))
            }
            
            # 如果保存了内容，添加文件路径信息
            if save_content and result.get('file_paths'):
                formatted_result["files_saved"] = {
                    "raw_data": result['file_paths'].get('raw_file'),
                    "parsed_data": result['file_paths'].get('parsed_file')
                }
                
                # 自动触发知识库处理
                try:
                    from utils.universal_knowledge_processor import UniversalKnowledgeProcessor
                    
                    # 创建知识库处理器实例
                    processor = UniversalKnowledgeProcessor()
                    
                    # 提取知识并保存
                    knowledge_data = processor.extract_knowledge(
                        content=parsed_data.get('content', ''),
                        title=parsed_data.get('title', ''),
                        url=url
                    )
                    
                    # 保存知识库
                    kb_filename = processor.save_knowledge_base(knowledge_data)
                    
                    # 添加知识库处理结果到返回信息
                    formatted_result["knowledge_base"] = {
                        "processed": True,
                        "filename": kb_filename,
                        "knowledge_count": len(knowledge_data.get('knowledge_items', []))
                    }
                    
                    logger.info(f"✅ 自动知识库处理完成: {kb_filename}")
                    
                except Exception as kb_error:
                    logger.warning(f"⚠️ 自动知识库处理失败: {str(kb_error)}")
                    formatted_result["knowledge_base"] = {
                        "processed": False,
                        "error": str(kb_error)
                    }
            
            return json.dumps(formatted_result, ensure_ascii=False, indent=2)
        else:
            # 返回错误信息
            error_result = {
                "status": "error",
                "url": url,
                "error": result.get('error', '未知错误'),
                "suggestions": [
                    "检查网络连接是否正常",
                    "确认URL是否可访问",
                    "检查网站是否有反爬虫机制",
                    "尝试稍后重试"
                ]
            }
            return json.dumps(error_result, ensure_ascii=False, indent=2)
            
    except ImportError as e:
        error_result = {
            "status": "error",
            "url": url,
            "error": f"导入WebpageCrawler模块失败: {str(e)}",
            "suggestions": [
                "确保webpage_crawler.py文件存在",
                "检查模块依赖是否正确安装"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)
    except Exception as e:
        error_result = {
            "status": "error",
            "url": url,
            "error": f"爬取过程中发生错误: {str(e)}",
            "suggestions": [
                "检查URL格式是否正确",
                "确认网络连接稳定",
                "查看详细错误日志"
            ]
        }
        return json.dumps(error_result, ensure_ascii=False, indent=2)

@mcp.tool()
def save_to_knowledge_base(json_data: str, base_filename: str = None, format_type: str = "dfd") -> str:
    """
    使用通用格式处理器保存知识库数据到独立文件中，支持多种格式类型
    """
    try:
        import json as _json
        
        # 解析输入的JSON数据
        data = _json.loads(json_data) if isinstance(json_data, str) else json_data
        
        # 创建指定格式类型的格式处理器
        processor = FormatProcessor(format_type=format_type)
        
        # 使用格式处理器保存数据
        result = processor.save_knowledge_base(data, base_filename)
        
        if result["success"]:
            saved_files = result["saved_files"]
            summary_file = result["summary_file"]
            statistics = result["statistics"]
            
            # 构建成功消息
            success_msg = f"[SUCCESS] {processor.get_format_name()}数据已保存到{len(saved_files)}个独立文件:\n"
            success_msg += "\n".join([f"- {file}" for file in saved_files])
            success_msg += f"\n\n汇总报告: {summary_file}\n\n统计信息:\n"
            
            # 动态生成统计信息
            for key, value in statistics.items():
                if key.endswith('_count'):
                    category_name = key.replace('_count', '').replace('dfd_', '')
                    success_msg += f"- {category_name}: {value} 个\n"
            
            return success_msg
        else:
            return f"[ERROR] 保存知识库数据失败: {result['error']}"
        
    except Exception as e:
        return f"[ERROR] 保存知识库数据失败: {str(e)}"

@mcp.tool()
def extract_universal_knowledge(content: str, url: str = "", title: str = "", 
                              requirement_type: str = "", target_conversion_type: str = "") -> str:
    """使用通用知识库格式提取知识
    
    Args:
        content: 要提取知识的文本内容
        url: 内容来源URL（可选）
        title: 内容标题（可选）
        requirement_type: 需求类型（如：自然语言需求、用户故事等）
        target_conversion_type: 目标转换类型（如：数据流图、用例图等）
    
    Returns:
        提取的通用知识库JSON字符串
    """
    try:
        # 使用通用知识库处理器提取知识
        knowledge_base = universal_processor.extract_knowledge(
            content=content,
            url=url,
            title=title,
            requirement_type=requirement_type,
            target_conversion_type=target_conversion_type
        )
        
        return json.dumps({
            "success": True,
            "message": "知识提取成功",
            "knowledge_base": knowledge_base
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"知识提取失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def extract_knowledge_with_ai(content: str, url: str = "", title: str = "", 
                             requirement_type: str = "", target_conversion_type: str = "",
                             prompt_type: str = "requirement_analysis") -> str:
    """使用AI提示词进行真正的知识提取
    
    Args:
        content: 要提取知识的文本内容
        url: 内容来源URL（可选）
        title: 内容标题（可选）
        requirement_type: 需求类型（如：自然语言需求、用户故事等）
        target_conversion_type: 目标转换类型（如：数据流图、用例图等）
        prompt_type: 使用的提示词类型（默认：requirement_analysis）
    
    Returns:
        AI提取的知识库JSON字符串
    """
    try:
        # 导入HTML清理器的新功能
        from utils.html_cleaner import clean_html_with_structure, is_html_content
        
        # 检查是否为HTML内容，如果是则进行结构化清理
        processed_content = content
        title_context = ""
        
        if is_html_content(content):
            logger.info("检测到HTML内容，进行结构化清理...")
            cleaning_result = clean_html_with_structure(content)
            processed_content = cleaning_result["cleaned_content"]
            
            # 如果有标题结构，格式化为上下文
            if cleaning_result["title_structure"]:
                from utils.html_cleaner import html_cleaner
                title_context = html_cleaner.format_title_structure_as_context(
                    cleaning_result["title_structure"]
                )
                logger.info(f"提取到 {len(cleaning_result['title_structure'])} 个标题结构")
        
        # 获取指定类型的系统提示词
        system_prompt = get_system_prompt(prompt_type)
        
        # 构建增强的用户提示词，包含标题结构上下文
        content_with_context = processed_content[:1500]  # 限制内容长度
        if title_context:
            content_with_context = f"{title_context}\n\n{content_with_context}"
        
        user_prompt = f"""请从以下内容中提取结构化知识：

**内容：**
{content_with_context}

请输出JSON格式，包含：
{{
  "generation_knowledge": {{
    "concepts": [
      {{"concept_id": "c1", "name": "概念名", "definition": "定义"}}
    ],
    "rules": [
      {{"rule_id": "r1", "name": "规则名", "description": "描述"}}
    ],
    "patterns": [
      {{"pattern_id": "p1", "name": "模式名", "description": "描述"}}
    ],
    "transformations": [
      {{"transformation_id": "t1", "name": "转换名", "description": "描述"}}
    ]
  }},
  "validation_knowledge": {{
    "criteria": [
      {{"criterion_id": "vc1", "name": "标准名", "description": "描述"}}
    ],
    "checklist": [
      {{"checklist_id": "cl1", "name": "检查项名", "description": "描述"}}
    ],
    "error_patterns": [
      {{"pattern_id": "ep1", "name": "错误模式名", "description": "描述"}}
    ]
  }},
  "examples": {{
    "input_examples": [
      {{"example_id": "in1", "name": "输入示例名", "description": "描述"}}
    ],
    "output_examples": [
      {{"example_id": "out1", "name": "输出示例名", "description": "描述"}}
    ]
  }}
}}

请确保每个数组字段至少有3条有效内容。如果内容不足，请基于专业知识补充合理的示例。"""

        # 调用AI模型
        response = openai_client.chat.completions.create(
            model=os.getenv("MODEL", "gpt-4"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # 降低随机性，提高一致性
            max_tokens=4000,  # 限制输出长度
            timeout=60  # 设置60秒超时
        )
        
        # 提取AI响应内容
        ai_response = response.choices[0].message.content
        
        # 尝试解析JSON以验证格式
        try:
            parsed_json = json.loads(ai_response)
            
            # 生成完整的知识库结构，包含元数据
            knowledge_base = {
                "metadata": {
                    "knowledge_id": f"ai_kb_{int(time.time())}",
                    "title": title or '未知标题',
                    "description": f"基于AI提取的知识库 - {title or '未知来源'}",
                    "version": "1.0",
                    "created_time": datetime.datetime.now().isoformat()
                },
                "generation_knowledge": parsed_json.get('generation_knowledge', parsed_json)
            }
            
            return json.dumps({
                "success": True,
                "message": "AI知识提取成功",
                "knowledge_base": knowledge_base,
                "extraction_method": "AI提示词驱动",
                "prompt_type": prompt_type
            }, ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            # 如果AI返回的不是有效JSON，尝试提取JSON部分
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group())
                    
                    # 生成完整的知识库结构，包含元数据
                    knowledge_base = {
                        "metadata": {
                            "knowledge_id": f"ai_kb_{int(time.time())}",
                            "title": title or '未知标题',
                            "description": f"基于AI提取的知识库 - {title or '未知来源'}",
                            "version": "1.0",
                            "created_time": datetime.datetime.now().isoformat()
                        },
                        "generation_knowledge": parsed_json.get('generation_knowledge', parsed_json)
                    }
                    
                    return json.dumps({
                        "success": True,
                        "message": "AI知识提取成功（从响应中提取JSON）",
                        "knowledge_base": knowledge_base,
                        "extraction_method": "AI提示词驱动",
                        "prompt_type": prompt_type
                    }, ensure_ascii=False, indent=2)
                except json.JSONDecodeError:
                    pass
            
            # 如果仍然无法解析，返回原始响应
            return json.dumps({
                "success": False,
                "message": "AI响应格式解析失败",
                "raw_response": ai_response,
                "error": "AI返回的内容不是有效的JSON格式"
            }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"AI知识提取失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def save_universal_knowledge_base(knowledge_base_json: str, output_dir: str = KNOWLEDGE_BASE_DIR) -> str:
    """保存通用知识库到文件
    
    Args:
        knowledge_base_json: 通用知识库JSON字符串
        output_dir: 输出目录路径
    
    Returns:
        保存结果的JSON字符串
    """
    try:
        # 解析知识库JSON
        knowledge_base = json.loads(knowledge_base_json)
        
        # 保存知识库
        filepath = universal_processor.save_knowledge_base(knowledge_base, output_dir)
        
        return json.dumps({
            "success": True,
            "message": "通用知识库保存成功",
            "filepath": filepath
        }, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"JSON解析错误: {str(e)}"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"保存失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

@mcp.tool()
def convert_to_universal_format(old_data_json: str, requirement_type: str = "", 
                               target_conversion_type: str = "") -> str:
    """将旧格式数据转换为通用知识库格式
    
    Args:
        old_data_json: 旧格式数据的JSON字符串
        requirement_type: 需求类型
        target_conversion_type: 目标转换类型
    
    Returns:
        转换后的通用知识库JSON字符串
    """
    try:
        # 解析旧格式数据
        old_data = json.loads(old_data_json)
        
        # 转换为通用格式
        new_knowledge_base = universal_processor.convert_from_old_format(
            old_data=old_data,
            requirement_type=requirement_type,
            target_conversion_type=target_conversion_type
        )
        
        return json.dumps({
            "success": True,
            "message": "格式转换成功",
            "knowledge_base": new_knowledge_base
        }, ensure_ascii=False, indent=2)
        
    except json.JSONDecodeError as e:
        return json.dumps({
            "success": False,
            "error": f"JSON解析错误: {str(e)}"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"格式转换失败: {str(e)}"
        }, ensure_ascii=False, indent=2)



# 全局变量用于存储WebSocket连接
websocket_connections = set()

def add_websocket_connection(websocket):
    """添加WebSocket连接"""
    websocket_connections.add(websocket)

def remove_websocket_connection(websocket):
    """移除WebSocket连接"""
    websocket_connections.discard(websocket)

async def send_realtime_feedback(message: str, log_type: str = "info"):
    """发送实时反馈到所有WebSocket连接"""
    if not websocket_connections:
        return
    
    log_data = {
        "type": log_type,
        "message": message,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    # 创建连接副本以避免在迭代时修改集合
    connections = list(websocket_connections)
    for websocket in connections:
        try:
            await websocket.send_json(log_data)
        except Exception:
            # 连接已断开，从集合中移除
            websocket_connections.discard(websocket)

@mcp.tool()
async def search_and_scrape_realtime(keyword: str, top_k: int = 12) -> str:
    """
    根据关键词搜索网页，并抓取前几个网页的图文信息。
    提供实时的过程反馈，每一步操作都会立即反馈给用户。
    """
    start_time = time.time()
    
    try:
        # 第一步：开始搜索
        await send_realtime_feedback("🔍 **第1步：开始搜索**", "search")
        await send_realtime_feedback(f"   关键词: {keyword}", "info")
        await send_realtime_feedback(f"   目标数量: {top_k} 个网页", "info")
        await send_realtime_feedback(f"   开始时间: {datetime.datetime.now().strftime('%H:%M:%S')}", "info")
        
        logger.info(f"开始搜索关键词: {keyword}")
        
        # 使用新的搜索框架获取详细信息（只使用Google搜索引擎）
        search_result = crawler.search_and_parse(default_search_engine, keyword, top_k)
        
        if not search_result["parsed_response"]["success"]:
            error_msg = f"搜索失败: {search_result['parsed_response'].get('error', '未知错误')}"
            await send_realtime_feedback(f"❌ {error_msg}", "error")
            return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)
        
        search_results = search_result["parsed_response"]["results"]
        await send_realtime_feedback(f"✅ 搜索完成！找到 {len(search_results)} 个结果", "info")
        await send_realtime_feedback(f"搜索引擎返回总数: {len(search_results)}", "info")
        
        # 第二步：显示搜索结果列表
        await send_realtime_feedback("📋 **第2步：搜索结果列表**", "search")
        for i, result in enumerate(search_results, 1):
            title = result.get('title', '无标题')[:50] + ('...' if len(result.get('title', '')) > 50 else '')
            url = result.get('url', '无URL')
            snippet = result.get('snippet', '无摘要')[:100] + ('...' if len(result.get('snippet', '')) > 100 else '')
            
            await send_realtime_feedback(f"{i}. {title}", "info")
            await send_realtime_feedback(f"   URL: `{url}`", "info")
            await send_realtime_feedback(f"   摘要: {snippet}", "info")
        
        # 第三步：开始爬取网页内容
        await send_realtime_feedback("🕷️ **第3步：开始爬取网页内容**", "search")
        await send_realtime_feedback(f"计划爬取 {len(search_results)} 个网页", "info")
        
        scraped_data = []
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, result in enumerate(search_results, 1):
            url = result.get('url', '')
            title = result.get('title', '无标题')
            
            # 实时反馈当前处理的网页
            await send_realtime_feedback(f"🔄 **正在处理第 {i}/{len(search_results)} 个网页**", "info")
            await send_realtime_feedback(f"标题: {title}", "info")
            await send_realtime_feedback(f"URL: `{url}`", "info")
            await send_realtime_feedback(f"时间: {datetime.datetime.now().strftime('%H:%M:%S')}", "info")
            
            if not url:
                await send_realtime_feedback("⚠️ 跳过：URL为空", "warning")
                skipped_count += 1
                continue
            
            # 检查是否重复
            dedup_instance = get_deduplication_instance()
            dedup_result = check_and_cache(url)
            
            if dedup_result.get('should_skip', False):
                await send_realtime_feedback(f"🔄 检测到重复网页，跳过爬取", "warning")
                cache_info = dedup_result.get('url_cache_info') or dedup_result.get('content_cache_info', {})
                await send_realtime_feedback(f"   缓存时间: {cache_info.get('last_crawled', 'N/A')}", "info")
                skipped_count += 1
                continue
            
            try:
                scrape_start_time = time.time()
                
                # 调用爬取工具
                scrape_result = await crawl_webpage_direct(url, save_content=True)
                scrape_result_data = json.loads(scrape_result)
                
                scrape_duration = time.time() - scrape_start_time
                
                if scrape_result_data.get("success", False):
                    await send_realtime_feedback(f"✅ 爬取成功 (耗时: {scrape_duration:.1f}秒)", "info")
                    content_length = len(scrape_result_data.get("content", ""))
                    await send_realtime_feedback(f"内容长度: {content_length} 字符", "info")
                    scraped_data.append(scrape_result_data)
                    success_count += 1
                else:
                    error_msg = scrape_result_data.get("error", "未知错误")
                    await send_realtime_feedback(f"❌ 爬取失败 (耗时: {scrape_duration:.1f}秒)", "error")
                    await send_realtime_feedback(f"错误信息: {error_msg}", "error")
                    failed_count += 1
                    
            except Exception as e:
                scrape_duration = time.time() - scrape_start_time
                await send_realtime_feedback(f"❌ 爬取失败 (耗时: {scrape_duration:.1f}秒)", "error")
                await send_realtime_feedback(f"错误信息: {str(e)}", "error")
                failed_count += 1
        
        # 第四步：处理完成统计
        total_duration = time.time() - start_time
        success_rate = (success_count / len(search_results) * 100) if search_results else 0
        
        await send_realtime_feedback("📊 **第4步：处理完成统计**", "search")
        await send_realtime_feedback(f"总耗时: {total_duration:.1f} 秒", "info")
        await send_realtime_feedback(f"成功爬取: {success_count} 个", "info")
        await send_realtime_feedback(f"爬取失败: {failed_count} 个", "error")
        await send_realtime_feedback(f"跳过重复: {skipped_count} 个", "warning")
        await send_realtime_feedback(f"成功率: {success_rate:.1f}%", "info")
        
        # 第五步：去重系统统计
        dedup_stats = get_stats()
        await send_realtime_feedback("🔄 **第5步：去重系统统计**", "search")
        await send_realtime_feedback(f"缓存中的网页数量: {dedup_stats.get('total_cached', 0)}", "info")
        await send_realtime_feedback(f"本次重复检测次数: {dedup_stats.get('check_count', 0)}", "info")
        
        # 组合最终结果
        final_result = {
            "success": True,
            "keyword": keyword,
            "search_results_count": len(search_results),
            "scraped_count": success_count,
            "failed_count": failed_count,
            "skipped_count": skipped_count,
            "success_rate": f"{success_rate:.1f}%",
            "total_duration": f"{total_duration:.1f}秒",
            "scraped_data": scraped_data,
            "deduplication_stats": dedup_stats
        }
        
        await send_realtime_feedback("🎉 **搜索爬取任务完成！**", "info")
        
        return json.dumps(final_result, ensure_ascii=False, indent=2)
        
    except Exception as e:
        error_msg = f"搜索爬取过程发生错误: {str(e)}"
        await send_realtime_feedback(f"❌ {error_msg}", "error")
        logger.error(error_msg, exc_info=True)
        return json.dumps({"success": False, "error": error_msg}, ensure_ascii=False)

@mcp.tool()
async def search_and_scrape(keyword: str, top_k: int = 12) -> str:
    """
    根据关键词搜索网页，并抓取前几个网页的图文信息。
    提供详细的过程反馈，包括搜索结果、爬取进度、失败信息等。
    """
    start_time = time.time()
    progress_info = []
    
    try:
        # 第一步：开始搜索
        progress_info.append("🔍 **第1步：开始搜索**")
        progress_info.append(f"   关键词: {keyword}")
        progress_info.append(f"   目标数量: {top_k} 个网页")
        progress_info.append(f"   开始时间: {datetime.datetime.now().strftime('%H:%M:%S')}")
        
        logger.info(f"开始搜索关键词: {keyword}")
        
        # 使用新的搜索框架获取详细信息（只使用Google搜索引擎）
        search_result = crawler.search_and_parse(default_search_engine, keyword, top_k)
        
        if not search_result["parsed_response"]["success"]:
            error_msg = search_result["parsed_response"].get("error", "未知搜索错误")
            progress_info.append(f"   ❌ 搜索失败: {error_msg}")
            logger.error(f"搜索失败: {error_msg}")
            return "\n".join(progress_info)
        
        # 提取搜索结果
        search_results = search_result["parsed_response"]["results"]
        total_found = search_result["parsed_response"].get("total_found", len(search_results))
        
        progress_info.append(f"   ✅ 搜索完成！找到 {len(search_results)} 个结果")
        progress_info.append(f"   搜索引擎返回总数: {total_found}")
        progress_info.append("")
        
        # 第二步：显示搜索到的网页列表
        progress_info.append("📋 **第2步：搜索结果列表**")
        for i, result in enumerate(search_results, 1):
            url = result.get("url", "未知URL")
            title = result.get("title", "无标题")[:50]
            snippet = result.get("snippet", "无摘要")[:80]
            progress_info.append(f"   {i}. {title}")
            progress_info.append(f"      URL: {url}")
            progress_info.append(f"      摘要: {snippet}...")
        progress_info.append("")
        
        if not search_results:
            progress_info.append("⚠️ 没有找到任何搜索结果")
            return "\n".join(progress_info)

        # 第三步：开始爬取网页
        progress_info.append("🕷️ **第3步：开始爬取网页内容**")
        progress_info.append(f"   计划爬取 {len(search_results)} 个网页")
        progress_info.append("")
        
        logger.info(f"找到 {len(search_results)} 个搜索结果，开始处理...")
        
        # 爬取内容
        summaries = []
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for i, result in enumerate(search_results):
            url = result.get("url", "")
            title = result.get("title", "无标题")
            
            try:
                progress_info.append(f"🔄 **正在处理第 {i+1}/{len(search_results)} 个网页**")
                progress_info.append(f"   标题: {title}")
                progress_info.append(f"   URL: {url}")
                progress_info.append(f"   时间: {datetime.datetime.now().strftime('%H:%M:%S')}")
                
                logger.info(f"正在处理第 {i+1} 个链接: {url}")
                
                # 添加延迟避免请求过快
                if i > 0:
                    await asyncio.sleep(1)
                
                # 检查是否为重复URL
                dedup_instance = get_deduplication_instance()
                is_duplicate, cache_info = dedup_instance.is_url_duplicate(url)
                
                if is_duplicate:
                    progress_info.append(f"   ⏭️ 跳过重复URL（已缓存）")
                    summaries.append(f"🔗 网页 {i+1}: {url}\n⏭️ 跳过重复URL（已在缓存中）\n")
                    skipped_count += 1
                    logger.info(f"第 {i+1} 个链接跳过（重复）")
                    continue
                
                # 开始爬取
                scrape_start = time.time()
                summary = await scrape_webpage(url)
                scrape_time = time.time() - scrape_start
                
                # 检查爬取结果
                if summary.startswith("[ERROR]") or "处理失败" in summary:
                    progress_info.append(f"   ❌ 爬取失败 (耗时: {scrape_time:.1f}秒)")
                    progress_info.append(f"   错误信息: {summary[:100]}...")
                    failed_count += 1
                else:
                    progress_info.append(f"   ✅ 爬取成功 (耗时: {scrape_time:.1f}秒)")
                    progress_info.append(f"   内容长度: {len(summary)} 字符")
                    success_count += 1
                
                summaries.append(f"🔗 网页 {i+1}: {url}\n{summary}\n")
                logger.info(f"第 {i+1} 个链接处理完成")
                progress_info.append("")
                
            except Exception as e:
                error_msg = str(e)
                progress_info.append(f"   ❌ 处理异常: {error_msg}")
                logger.warning(f"处理网页 {url} 时出错: {error_msg}")
                summaries.append(f"🔗 网页 {i+1}: {url}\n❌ 处理失败: {error_msg}\n")
                failed_count += 1
                progress_info.append("")

        # 第四步：汇总统计信息
        total_time = time.time() - start_time
        progress_info.append("📊 **第4步：处理完成统计**")
        progress_info.append(f"   总耗时: {total_time:.1f} 秒")
        progress_info.append(f"   成功爬取: {success_count} 个")
        progress_info.append(f"   爬取失败: {failed_count} 个")
        progress_info.append(f"   跳过重复: {skipped_count} 个")
        progress_info.append(f"   成功率: {(success_count/(success_count+failed_count)*100):.1f}%" if (success_count+failed_count) > 0 else "0%")
        
        if not summaries:
            progress_info.append("⚠️ 所有网页处理都失败了")
            return "\n".join(progress_info)

        # 添加去重统计信息
        try:
            dedup_instance = get_deduplication_instance()
            stats = dedup_instance.get_stats()
            progress_info.append("")
            progress_info.append("🗂️ **去重系统统计**")
            progress_info.append(f"   URL缓存数量: {stats.get('url_count', 0)} 个")
            progress_info.append(f"   内容缓存数量: {stats.get('content_count', 0)} 个")
            progress_info.append(f"   跳过重复URL: {stats.get('url_duplicates', 0)} 次")
            progress_info.append(f"   检测重复内容: {stats.get('content_duplicates', 0)} 次")
        except Exception as e:
            logger.warning(f"获取去重统计失败: {str(e)}")
        
        # 组合最终结果
        final_result = "\n".join(progress_info) + "\n\n" + "="*50 + "\n📄 **爬取内容详情**\n" + "="*50 + "\n\n" + "\n\n".join(summaries)
        return final_result
        
    except Exception as e:
        error_msg = str(e)
        progress_info.append(f"❌ **系统错误**: {error_msg}")
        logger.error(f"搜索或抓取过程中出错: {error_msg}")
        return "\n".join(progress_info)

@mcp.tool()
def manage_web_deduplication(action: str = "stats", days: int = 7) -> str:
    """
    管理网页去重系统
    
    Args:
        action: 操作类型 ("stats" - 查看统计, "clean" - 清理缓存, "reset" - 重置所有)
        days: 清理多少天前的缓存 (仅在action="clean"时有效)
    """
    try:
        dedup_instance = get_deduplication_instance()
        
        if action == "stats":
            stats = dedup_instance.get_stats()
            return json.dumps({
                "status": "success",
                "action": "统计信息",
                "data": {
                    "URL缓存数量": f"{stats.get('url_count', 0)} 个",
                    "内容缓存数量": f"{stats.get('content_count', 0)} 个",
                    "跳过重复URL次数": f"{stats.get('url_duplicates', 0)} 次",
                    "检测重复内容次数": f"{stats.get('content_duplicates', 0)} 次",
                    "数据库文件": "web_cache.db"
                }
            }, ensure_ascii=False, indent=2)
            
        elif action == "clean":
            cleaned_count = dedup_instance.clean_old_cache(days)
            return json.dumps({
                "status": "success",
                "action": "清理缓存",
                "message": f"已清理 {days} 天前的缓存",
                "cleaned_count": cleaned_count
            }, ensure_ascii=False, indent=2)
            
        elif action == "reset":
            dedup_instance.reset_cache()
            return json.dumps({
                "status": "success",
                "action": "重置缓存",
                "message": "所有缓存已清空"
            }, ensure_ascii=False, indent=2)
            
        else:
            return json.dumps({
                "status": "error",
                "message": "无效的操作类型，支持: stats, clean, reset"
            }, ensure_ascii=False, indent=2)
            
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"去重系统管理失败: {str(e)}"
        }, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # 初始化数据库
    # asyncio.run(init_db()) # 删除所有数据库相关的调用和逻辑
    
    # 启动MCP服务器
    # MCP server starting...
    
    # 如果启用了Tor，自动启动Tor代理
    if USE_TOR and tor_manager:
        # Tor proxy enabled, auto-starting...
        success = tor_manager.start_tor()
        if success:
            # SUCCESS: Tor proxy auto-start successful
            pass
        else:
            # ERROR: Tor proxy auto-start failed, using normal network connection
            pass
    
    try:
        mcp.run(transport='stdio')
    finally:
        # 程序退出时清理Tor资源
        if USE_TOR and tor_manager:
            # Cleaning up Tor resources...
            tor_manager.cleanup()
    # 在程序退出前关闭数据库连接池
    # asyncio.run(close_pool()) # 删除所有数据库相关的调用和逻辑
