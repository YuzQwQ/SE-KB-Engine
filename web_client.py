import asyncio
import datetime
import os
import json
import sys
from typing import Optional
from contextlib import AsyncExitStack
from openai import OpenAI
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import zipfile
import tempfile
import weakref

load_dotenv()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    timestamp: str


class MCPWebClient:
    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("BASE_URL")
        self.model = os.getenv("MODEL")

        # 允许在未配置 API Key 的情况下启动，仅禁用聊天功能
        if self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)
        else:
            self.client = None
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.history = []
        self.websocket_connections = weakref.WeakSet()
        
        # 初始化FastAPI应用
        self.app = FastAPI(title="MCP Client Web Interface", version="1.0.0")
        self.setup_routes()

    async def send_log(self, log_type: str, message: str):
        """向所有WebSocket连接发送日志消息"""
        if not self.websocket_connections:
            return
        
        log_data = {
            "type": log_type,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # 创建连接副本以避免在迭代时修改集合
        connections = list(self.websocket_connections)
        for websocket in connections:
            try:
                await websocket.send_json(log_data)
            except Exception as e:
                # 连接已断开，从集合中移除
                try:
                    self.websocket_connections.discard(websocket)
                except:
                    pass

    async def parse_and_send_step_feedback(self, feedback_text: str):
        """解析分步骤的反馈信息并实时发送"""
        lines = feedback_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 根据内容确定日志类型
            if line.startswith('🔍') or line.startswith('📋') or line.startswith('🕷️') or line.startswith('📊') or line.startswith('🔄'):
                # 步骤标题
                await self.send_log("search", line)
            elif line.startswith('✅'):
                # 成功信息
                await self.send_log("info", line)
            elif line.startswith('❌'):
                # 错误信息
                await self.send_log("error", line)
            elif line.startswith('⚠️'):
                # 警告信息
                await self.send_log("warning", line)
            elif line.startswith('🎉'):
                # 完成信息
                await self.send_log("info", line)
            else:
                # 普通信息
                await self.send_log("info", line)
            
            # 添加小延迟以模拟实时效果
            await asyncio.sleep(0.1)

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("服务器脚本必须是 .py 或 .js 文件")

        command = sys.executable if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.session.initialize()
        response = await self.session.list_tools()
        print(f"✅ 已连接到服务器，可用工具: {[tool.name for tool in response.tools]}")

    async def process_query(self, query: str) -> str:
        await self.send_log("info", f"收到用户查询: {query}")
        
        # 若未配置 OpenAI Key，则直接返回提示，避免阻塞其他工具功能
        if self.client is None:
            await self.send_log("warning", "未配置 OpenAI API Key，聊天功能已禁用。请在 .env 设置 OPENAI_API_KEY 后再试。")
            return (
                "未配置 OpenAI API Key，聊天功能不可用。\n"
                "但搜索与爬取工具仍可用：请使用 /api/crawl 或 /api/search_extract_universal 接口。"
            )
        
        if not self.history:
            self.history.append({
                "role": "system",
                "content": (
                    "你是一位专业的需求转换DFD知识提取专家。\n\n"
                    "工具使用规则：\n"
                    "1) 任何涉及搜索、爬取、最新信息的请求，必须调用工具。\n"
                    "2) 使用 search_and_parse_universal 进行一站式搜索、解析和内容提取。\n"
                    "3) 根据需要设置 extract_content 参数控制是否进行内容提取。\n"
                    "4) 注意：scrape_and_extract_universal 工具已被删除，请使用 search_and_parse_universal 替代。\n\n"
                    "可用的主要工具：\n"
                    "- search_and_parse_universal: 一站式搜索、解析和内容提取\n"
                    "- extract_universal_knowledge: 直接从文本内容提取知识\n"
                    "- scrape_webpage: 抓取单个网页内容\n"
                    "- get_available_search_engines: 获取可用搜索引擎列表\n\n"
                    "回复要求：\n"
                    "- 完成搜索爬取任务后，简要说明已完成的操作和获取的主要内容。\n"
                    "- 提供核心知识点的结构化总结，包括概念、方法、步骤等。\n"
                    "- 保持友好专业的语调，给出有价值的信息反馈。\n"
                    "- 避免输出大量无效URL或格式错误的内容。\n"
                    "- 简洁明了，突出重点，避免冗余。"
                )
            })
        self.history.append({"role": "user", "content": query})

        messages = self.history.copy()

        # 获取当前支持的工具列表
        await self.send_log("info", "获取可用工具列表...")
        tool_response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in tool_response.tools]

        # 第一次调用 - 看模型想不想调用工具
        await self.send_log("info", "正在分析查询并决定是否需要调用工具...")
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=available_tools,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message
        messages.append({
            "role": "assistant",
            "content": assistant_message.content,
            "tool_calls": [tool_call.model_dump() for tool_call in assistant_message.tool_calls] if assistant_message.tool_calls else None
        })

        # 如果模型想调用工具
        if assistant_message.tool_calls:
            await self.send_log("info", f"需要调用 {len(assistant_message.tool_calls)} 个工具")
            
            # 获取可用工具名称列表用于验证
            available_tool_names = [tool.name for tool in tool_response.tools]
            
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                # 验证工具是否存在
                if function_name not in available_tool_names:
                    error_message = f"❌ 工具 '{function_name}' 不存在。可用工具: {', '.join(available_tool_names)}"
                    await self.send_log("error", error_message)
                    
                    # 如果是已删除的工具，提供替代建议
                    if function_name == "scrape_and_extract_universal":
                        suggestion = "请使用 'search_and_parse_universal' 工具，它已整合了搜索、解析和内容提取功能。"
                        await self.send_log("info", f"💡 建议: {suggestion}")
                        error_message += f" {suggestion}"
                    
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.id
                    })
                    continue

                await self.send_log("search", f"🔧 调用工具: {function_name}")
                await self.send_log("info", f"📝 参数: {json.dumps(function_args, ensure_ascii=False, indent=2)}")

                try:
                    # 根据工具类型设置不同的超时时间
                    if function_name in ['search_and_scrape', 'search_and_parse_universal']:
                        timeout_seconds = 3600.0  # 搜索爬取工具1小时超时
                        await self.send_log("warning", f"⏱️ 搜索爬取工具超时设置: {timeout_seconds/60:.0f}分钟")
                    else:
                        timeout_seconds = 1800.0  # 其他工具30分钟超时
                        await self.send_log("info", f"⏱️ 工具超时设置: {timeout_seconds/60:.0f}分钟")
                    
                    await self.send_log("info", "🚀 开始执行工具...")
                    
                    # 调用MCP工具，设置超时时间
                    result = await asyncio.wait_for(
                        self.session.call_tool(function_name, function_args),
                        timeout=timeout_seconds
                    )
                    tool_result = json.dumps([content.model_dump() for content in result.content], ensure_ascii=False)
                    
                    # 显示工具的详细反馈信息
                    if result.content and len(result.content) > 0:
                        for content in result.content:
                            if hasattr(content, 'text') and content.text:
                                # 检查是否是分步骤的反馈信息
                                if function_name in ['search_and_scrape', 'search_and_scrape_realtime']:
                                    # 解析分步骤的反馈并实时发送
                                    await self.parse_and_send_step_feedback(content.text)
                                else:
                                    # 将工具返回的文本内容作为日志发送
                                    await self.send_log("info", content.text)
                    
                    await self.send_log("info", f"✅ 工具调用成功，返回数据长度: {len(tool_result)} 字符")
                    
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_call.id
                    })
                except asyncio.TimeoutError:
                    timeout_minutes = int(timeout_seconds / 60)
                    error_message = f"⏰ 工具调用超时: {function_name} 执行时间超过{timeout_minutes}分钟，请尝试使用更具体的关键词或减少搜索范围"
                    await self.send_log("error", error_message)
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.id
                    })
                except Exception as e:
                    error_message = f"工具调用失败: {str(e)}"
                    await self.send_log("error", error_message)
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.id
                    })

            # 第二次调用 - 让模型处理工具结果
            await self.send_log("info", "🤖 正在生成AI回复...")
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            final_content = final_response.choices[0].message.content or ""
            await self.send_log("info", f"✅ AI回复生成完成，长度: {len(final_content)} 字符")
        else:
            final_content = assistant_message.content or ""
            await self.send_log("info", "💬 直接回复，无需调用工具")

        # 当模型返回空内容时的兜底文案
        if not isinstance(final_content, str):
            final_content = str(final_content) if final_content is not None else ""
        if not final_content.strip():
            final_content = (
                "这次没有生成文本回复。"
                "如果你要进行‘搜索并爬取’，请直接输入：搜索并爬取 <关键词>，"
                "或调用 /api/search_extract_universal 接口。"
            )

        # 将最终回复加入历史记录
        self.history.append({"role": "assistant", "content": final_content})
        
        return final_content

    def setup_routes(self):
        # 静态文件服务
        static_path = Path(__file__).parent / "static"
        if static_path.exists():
            self.app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        @self.app.get("/", response_class=HTMLResponse)
        async def read_root():
            html_file = static_path / "index.html"
            if html_file.exists():
                return HTMLResponse(content=html_file.read_text(encoding='utf-8'))
            else:
                return HTMLResponse(content="<h1>MCP Client Web Interface</h1><p>静态文件未找到</p>")
                
        @self.app.get("/debug")
        async def debug_page():
            return FileResponse("static/debug.html")

        @self.app.websocket("/ws/logs")
        async def websocket_logs(websocket: WebSocket):
            await websocket.accept()
            self.websocket_connections.add(websocket)
            try:
                # 发送连接成功消息
                await self.send_log("system", "WebSocket连接已建立")
                # 保持连接
                while True:
                    await websocket.receive_text()
            except WebSocketDisconnect:
                pass
            except Exception as e:
                print(f"WebSocket错误: {e}")
            finally:
                try:
                    self.websocket_connections.discard(websocket)
                except:
                    pass

        @self.app.post("/api/crawl")
        async def crawl_endpoint(request: Request):
            try:
                if not self.session:
                    raise HTTPException(status_code=500, detail="MCP服务器未连接")
                
                body = await request.json()
                theme = body.get("theme")
                search_content = body.get("search_content")
                
                if not theme or not search_content:
                    raise HTTPException(status_code=400, detail="缺少主题或搜索内容")
                
                # 主题到工具类型的映射
                theme_to_tool_mapping = {
                    "general": "general",
                    "universal_knowledge": "universal_knowledge", 
                    "requirement_analysis": "requirement_analysis",
                    "dfd_expert": "dfd_expert",
                    "system_design": "system_design",
                    "requirement_to_dfd": "requirement_to_dfd"
                }
                
                tool_type = theme_to_tool_mapping.get(theme)
                if not tool_type:
                    raise HTTPException(status_code=400, detail=f"不支持的主题: {theme}")
                
                # 可选参数
                engine = body.get("engine", "google")
                max_results = int(body.get("max_results", 10))
                use_ai = bool(body.get("use_ai", True))
                prompt_type_override = body.get("prompt_type")
                target_conversion_type = body.get("target_conversion_type") or ("DFD图" if "dfd" in theme.lower() else "知识库")
                
                await self.send_log("info", f"开始爬取 - 主题: {theme}, 搜索内容: {search_content}, 引擎: {engine}, 数量: {max_results}, AI: {use_ai}")
                
                # 调用对应的搜索工具（支持AI增强模式）
                search_args = {
                    "engine": engine,
                    "keyword": search_content,
                    "max_results": max_results,
                    "extract_content": True,
                    "requirement_type": tool_type,
                    "target_conversion_type": target_conversion_type,
                    "auto_save": True,
                    "use_ai": use_ai,
                    "prompt_type": prompt_type_override or tool_type
                }
                
                # 为整个处理过程设置超时
                search_res = await asyncio.wait_for(
                    self.session.call_tool("search_and_parse_universal", search_args),
                    timeout=7200.0  # 2小时超时
                )
                
                # 解析工具返回结果
                try:
                    dumped = [c.model_dump() for c in search_res.content]
                    parsed_json = json.loads(dumped[0].get("text", dumped[0].get("content", "")))
                except Exception as e:
                    await self.send_log("error", f"解析搜索结果失败: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"解析搜索结果失败: {str(e)}")
                
                # 提取结果信息
                content_extraction = parsed_json.get("content_extraction", {})
                extracted_knowledge = content_extraction.get("extracted_knowledge", [])
                
                kb_list = []
                saved_paths = []
                
                for item in extracted_knowledge:
                    kb_data = {
                        "url": item.get("url"),
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "knowledge_base": item.get("knowledge_base"),
                        "extraction_success": item.get("extraction_success", False),
                        "extraction_method": item.get("extraction_method")
                    }
                    kb_list.append(kb_data)
                    
                    if "saved_filepath" in item:
                        saved_paths.append(item["saved_filepath"])
                
                # 处理失败的提取
                failed_urls = content_extraction.get("failed_urls", [])
                for failed in failed_urls:
                    kb_list.append({
                        "url": failed.get("url"),
                        "error": failed.get("error", "提取失败"),
                        "extraction_success": False
                    })
                
                successful_count = content_extraction.get("successful_extractions", 0)
                total_count = content_extraction.get("total_urls_processed", 0)
                
                await self.send_log("success", f"爬取完成 - 成功: {successful_count}/{total_count}")
                
                return JSONResponse({
                    "success": True,
                    "theme": theme,
                    "search_content": search_content,
                    "processed_urls": total_count,
                    "successful_extractions": successful_count,
                    "failed_extractions": content_extraction.get("failed_extractions", 0),
                    "knowledge_bases": kb_list,
                    "saved_filepaths": saved_paths,
                    "timestamp": datetime.datetime.now().isoformat()
                })
                
            except asyncio.TimeoutError:
                await self.send_log("error", "爬取请求超时")
                raise HTTPException(status_code=408, detail="请求处理超时，请稍后重试")
            except HTTPException:
                raise
            except Exception as e:
                await self.send_log("error", f"爬取过程出错: {str(e)}")
                print(f"❌ 处理爬取请求时出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

        @self.app.post("/api/semantic-search")
        async def semantic_search_endpoint(request: Request):
            """语义搜索接口"""
            try:
                if not self.session:
                    raise HTTPException(status_code=500, detail="MCP服务器未连接")
                
                body = await request.json()
                query = body.get("query")
                intent = body.get("intent")  # Optional
                top_k = int(body.get("top_k", 5))
                
                if not query:
                    raise HTTPException(status_code=400, detail="缺少查询内容 (query)")
                
                # 调用 search_knowledge 工具
                result = await self.session.call_tool(
                    "search_knowledge", 
                    arguments={
                        "query": query,
                        "intent": intent,
                        "top_k": top_k
                    }
                )
                
                # 解析工具返回的 JSON 字符串
                # result.content 是一个 list，通常第一个元素是 TextContent
                if result.content and hasattr(result.content[0], "text"):
                    search_result = json.loads(result.content[0].text)
                    return search_result
                else:
                    return {"error": "No content returned from search tool"}
                
            except Exception as e:
                print(f"❌ 语义搜索失败: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/chat", response_model=ChatResponse)
        async def chat_endpoint(request: ChatRequest):
            try:
                if not self.session:
                    raise HTTPException(status_code=500, detail="MCP服务器未连接")
                
                # 为整个处理过程设置超时
                response = await asyncio.wait_for(
                    self.process_query(request.message),
                    timeout=7200.0  # 2小时超时，基本移除时间限制
                )
                return ChatResponse(
                    response=response,
                    timestamp=datetime.datetime.now().isoformat()
                )
            except asyncio.TimeoutError:
                print(f"⏰ 聊天请求超时: 处理时间超过2小时")
                raise HTTPException(status_code=408, detail="请求处理超时，请稍后重试")
            except Exception as e:
                print(f"❌ 处理聊天请求时出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

        @self.app.post("/api/search_extract_universal")
        async def search_extract_universal(request: Request):
            try:
                if not self.session:
                    raise HTTPException(status_code=500, detail="MCP服务器未连接")
                body = await request.json()
                keyword = body.get("keyword")
                if not keyword:
                    raise HTTPException(status_code=400, detail="缺少keyword")
                engine = body.get("engine", "google")
                max_results = int(body.get("max_results", 10))
                per_url_limit = int(body.get("per_url_limit", 3))
                requirement_type = body.get("requirement_type", "需求分析")
                target_conversion_type = body.get("target_conversion_type", "DFD图")
                auto_save = bool(body.get("auto_save", True))

                # 调用增强的搜索解析工具，一次性完成搜索和内容提取
                search_args = {
                    "engine": engine, 
                    "keyword": keyword, 
                    "max_results": max_results,
                    "extract_content": True,
                    "requirement_type": requirement_type,
                    "target_conversion_type": target_conversion_type,
                    "auto_save": auto_save
                }
                search_res = await self.session.call_tool("search_and_parse_universal", search_args)
                
                # 解析工具返回
                try:
                    dumped = [c.model_dump() for c in search_res.content]
                    parsed_json = json.loads(dumped[0].get("text", dumped[0].get("content", "")))
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"解析搜索结果失败: {str(e)}")

                # 从增强工具的返回结果中提取知识库数据
                kb_list = []
                saved_paths = []
                
                content_extraction = parsed_json.get("content_extraction", {})
                extracted_knowledge = content_extraction.get("extracted_knowledge", [])
                
                for item in extracted_knowledge:
                    kb_data = {
                        "url": item.get("url"),
                        "title": item.get("title"),
                        "snippet": item.get("snippet"),
                        "knowledge_base": item.get("knowledge_base"),
                        "extraction_success": item.get("extraction_success", False)
                    }
                    kb_list.append(kb_data)
                    
                    # 收集保存的文件路径
                    if "saved_filepath" in item:
                        saved_paths.append(item["saved_filepath"])
                
                # 处理失败的提取
                failed_urls = content_extraction.get("failed_urls", [])
                for failed in failed_urls:
                    kb_list.append({
                        "url": failed.get("url"),
                        "error": failed.get("error", "提取失败"),
                        "extraction_success": False
                    })

                return JSONResponse({
                    "success": True,
                    "keyword": keyword,
                    "engine": engine,
                    "processed_urls": content_extraction.get("total_urls_processed", 0),
                    "successful_extractions": content_extraction.get("successful_extractions", 0),
                    "failed_extractions": content_extraction.get("failed_extractions", 0),
                    "knowledge_bases": kb_list,
                    "saved_filepaths": saved_paths,
                    "timestamp": datetime.datetime.now().isoformat()
                })
            except HTTPException:
                raise
            except Exception as e:
                print(f"❌ search_extract_universal 出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

        @self.app.get("/api/health")
        async def health_check():
            return {
                "status": "healthy",
                "mcp_connected": self.session is not None,
                "timestamp": datetime.datetime.now().isoformat()
            }

        @self.app.get("/api/files")
        async def list_crawled_files():
            """获取所有爬取结果文件列表"""
            try:
                data_dir = Path("data")
                files_info = []
                
                if data_dir.exists():
                    # 获取raw文件
                    raw_dir = data_dir / "raw"
                    if raw_dir.exists():
                        for file_path in raw_dir.glob("*.json"):
                            files_info.append({
                                "name": file_path.name,
                                "type": "raw",
                                "path": str(file_path),
                                "size": file_path.stat().st_size,
                                "modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            })
                    
                    # 获取parsed文件
                    parsed_dir = data_dir / "parsed"
                    if parsed_dir.exists():
                        for file_path in parsed_dir.glob("*.json"):
                            files_info.append({
                                "name": file_path.name,
                                "type": "parsed",
                                "path": str(file_path),
                                "size": file_path.stat().st_size,
                                "modified": datetime.datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                            })
                
                # 按修改时间排序，最新的在前
                files_info.sort(key=lambda x: x["modified"], reverse=True)
                
                return {
                    "files": files_info,
                    "total_count": len(files_info),
                    "timestamp": datetime.datetime.now().isoformat()
                }
            except Exception as e:
                print(f"❌ 获取文件列表时出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

        @self.app.get("/api/download/{file_type}/{file_name}")
        async def download_file(file_type: str, file_name: str):
            """下载单个文件"""
            try:
                if file_type not in ["raw", "parsed"]:
                    raise HTTPException(status_code=400, detail="无效的文件类型")
                
                data_dir = Path("data")
                file_path = data_dir / file_type / file_name
                
                if not file_path.exists():
                    raise HTTPException(status_code=404, detail="文件不存在")
                
                return FileResponse(
                    path=str(file_path),
                    filename=file_name,
                    media_type="application/json"
                )
            except HTTPException:
                raise
            except Exception as e:
                print(f"❌ 下载文件时出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")

        @self.app.get("/api/download-all")
        async def download_all_files():
            """下载所有爬取结果文件的压缩包"""
            try:
                data_dir = Path("data")
                if not data_dir.exists():
                    raise HTTPException(status_code=404, detail="没有找到爬取数据")
                
                # 创建临时zip文件
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
                temp_file.close()
                
                with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # 添加raw文件
                    raw_dir = data_dir / "raw"
                    if raw_dir.exists():
                        for file_path in raw_dir.glob("*.json"):
                            zipf.write(file_path, f"raw/{file_path.name}")
                    
                    # 添加parsed文件
                    parsed_dir = data_dir / "parsed"
                    if parsed_dir.exists():
                        for file_path in parsed_dir.glob("*.json"):
                            zipf.write(file_path, f"parsed/{file_path.name}")
                
                # 生成文件名
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"crawled_data_{timestamp}.zip"
                
                return FileResponse(
                    path=temp_file.name,
                    filename=filename,
                    media_type="application/zip",
                    background=lambda: Path(temp_file.name).unlink(missing_ok=True)  # 下载后删除临时文件
                )
            except HTTPException:
                raise
            except Exception as e:
                print(f"❌ 创建压缩包时出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"创建压缩包失败: {str(e)}")

    async def cleanup(self):
        await self.exit_stack.aclose()

    async def start_server(self, host: str = "127.0.0.1", port: int = 8000):
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        print(f"🌐 Web服务器启动中...")
        print(f"📱 访问地址: http://{host}:{port}")
        print(f"🔗 API文档: http://{host}:{port}/docs")
        
        await server.serve()


async def main():
    client = MCPWebClient()
    
    try:
        # 连接到MCP服务器
        server_script = "server.py"
        await client.connect_to_server(server_script)
        
        # 启动Web服务器
        # 使用 0.0.0.0 允许外部访问，127.0.0.1 仅限本地访问
        host = os.getenv("WEB_HOST", "127.0.0.1")  # 可通过环境变量配置
        port = int(os.getenv("WEB_PORT", "8000"))   # 可通过环境变量配置
        await client.start_server(host=host, port=port)
        
    except KeyboardInterrupt:
        print("\n👋 正在关闭服务器...")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())