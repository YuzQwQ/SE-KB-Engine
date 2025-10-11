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
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import zipfile
import tempfile

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

        if not self.openai_api_key:
            raise ValueError("❌ 未找到 OpenAI API Key，请在 .env 文件中设置OPENAI_API_KEY")

        self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.history = []
        
        # 初始化FastAPI应用
        self.app = FastAPI(title="MCP Client Web Interface", version="1.0.0")
        self.setup_routes()

    async def connect_to_server(self, server_script_path: str):
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("服务器脚本必须是 .py 或 .js 文件")

        command = "python" if is_python else "node"
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
        if not self.history:
            self.history.append({
                "role": "system",
                "content": (
                    "你是一位专业的网页内容爬取与分析专家。你的主要职责是帮助用户高效地收集、分析和整理各种网页内容和在线资源。\n\n"
                    
                    "⚠️ 重要工作规则：\n"
                    "当用户请求获取、搜索、爬取任何网络信息或知识时，你必须优先使用相关工具，而不是依赖自己的知识库回答。\n"
                    "- 如果用户询问任何需要最新信息的内容，必须使用 search_and_scrape 工具\n"
                    "- 如果用户要求爬取特定网站内容，必须使用 crawl_webpage_direct 或 scrape_webpage 工具\n"
                    "- 如果用户需要某个主题的详细资料，必须先搜索和爬取相关网页内容\n"
                    "- 只有在工具调用失败或用户明确要求基于已有知识回答时，才可以使用自己的知识库\n\n"
                    
                    "🎯 你的专业领域：\n"
                    "- 网页内容抓取和数据提取\n"
                    "- 多种格式内容的智能解析（HTML、JSON、XML等）\n"
                    "- 搜索引擎结果分析和信息聚合\n"
                    "- 内容结构化处理和数据清洗\n"
                    "- 反爬虫策略和网络请求优化\n\n"
                    
                    "🔧 你的核心功能：\n"
                    "1. 🔍 智能搜索与内容发现\n"
                    "- 使用 `search_and_scrape` 工具进行关键词搜索和批量内容抓取\n"
                    "- 自动识别和筛选高质量的相关内容\n"
                    "- 支持多种搜索引擎和内容源\n\n"
                    
                    "2. 🌐 精准网页内容分析\n"
                    "- 使用 `scrape_webpage` 工具深度解析目标网页（支持代理）\n"
                    "- 使用 `crawl_webpage_direct` 工具直接爬取网页（无代理，适合CSDN等网站）\n"
                    "- 提取文本、链接、图片、表格等各类内容元素\n"
                    "- 智能识别页面结构和关键信息\n\n"
                    
                    "3. 🛡️ 高效反爬虫策略\n"
                    "- 智能请求头设置和用户代理轮换\n"
                    "- 合理的请求间隔和重试机制\n"
                    "- 遵守robots.txt和网站使用条款\n"
                    "- 支持代理服务和Tor网络（可选配置）\n\n"
                    
                    "4. 📊 内容结构化存储\n"
                    "- 自动将爬取的内容整理成结构化的JSON格式\n"
                    "- 包含标题、摘要、正文、来源链接等关键信息\n"
                    "- 同时生成便于阅读的Markdown格式文档\n"
                    "- 支持自定义数据格式和字段配置\n\n"
                    
                    "5. 💬 专业咨询服务\n"
                    "- 为用户提供网页爬取策略建议\n"
                    "- 解答关于内容分析和数据处理的问题\n"
                    "- 协助优化爬取效率和数据质量\n"
                    "- 提供技术方案和最佳实践指导\n\n"
                    
                    "🎯 适用场景：\n"
                    "- 学术研究和资料收集\n"
                    "- 市场调研和竞品分析\n"
                    "- 新闻资讯和舆情监控\n"
                    "- 技术文档和知识库构建\n"
                    "- 电商数据和价格监控\n"
                    "- 社交媒体内容分析\n\n"
                    
                    "工作原则：\n"
                    "1. 优先使用工具获取最新、准确的网络信息，而非依赖内置知识\n"
                    "2. 确保数据的结构化存储和便于后续处理\n"
                    "3. 提供清晰、专业的分析结果和建议\n"
                    "4. 严格遵循网络爬虫的最佳实践和道德规范\n"
                    "5. 尊重网站版权和使用条款，合理控制访问频率\n"
                )
            })

        # 添加用户消息到历史记录
        self.history.append({"role": "user", "content": query})

        messages = self.history.copy()

        # 获取当前支持的工具列表
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
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                print(f"🔧 调用工具: {function_name}")
                print(f"📝 参数: {json.dumps(function_args, ensure_ascii=False, indent=2)}")

                try:
                    # 调用MCP工具
                    result = await self.session.call_tool(function_name, function_args)
                    tool_result = json.dumps([content.model_dump() for content in result.content], ensure_ascii=False)
                    
                    print(f"✅ 工具调用成功")
                    
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": tool_call.id
                    })
                except Exception as e:
                    error_message = f"工具调用失败: {str(e)}"
                    print(f"❌ {error_message}")
                    messages.append({
                        "role": "tool",
                        "content": error_message,
                        "tool_call_id": tool_call.id
                    })

            # 第二次调用 - 让模型处理工具结果
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            final_content = final_response.choices[0].message.content
        else:
            final_content = assistant_message.content

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

        @self.app.post("/api/chat", response_model=ChatResponse)
        async def chat_endpoint(request: ChatRequest):
            try:
                if not self.session:
                    raise HTTPException(status_code=500, detail="MCP服务器未连接")
                
                response = await self.process_query(request.message)
                return ChatResponse(
                    response=response,
                    timestamp=datetime.datetime.now().isoformat()
                )
            except Exception as e:
                print(f"❌ 处理聊天请求时出错: {str(e)}")
                raise HTTPException(status_code=500, detail=f"处理请求时出错: {str(e)}")

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