# SE-KB 知识库系统演进方案 (MCP-First 架构)

## 1. 愿景与目标

构建一个面向未来的**软件工程知识加工系统**。不仅服务于 Web 界面用户，更核心的是作为**Agent 生态的基础设施**，通过 MCP (Model Context Protocol) 标准，让 Cursor、Claude Desktop 等外部 Agent 能够零成本接入并利用该知识库进行推理和生成。

## 2. 核心架构：MCP-First 策略

系统将采用 **"MCP Server 为核，Web Client 为壳"** 的设计模式。所有核心能力（检索、读取、推理）优先封装为 MCP 协议，Web 界面仅作为 MCP 的一个可视化客户端。

```mermaid
graph TD
    User[用户 (Web界面)] --> |HTTP| WebAPI[Web API Gateway (FastAPI)]
    ExternalAgent[外部 Agent (Cursor/Claude)] --> |MCP Protocol| MCPServer
    WebAPI --> |MCP Protocol| MCPServer[SE-KB MCP Server]
    
    subgraph "SE-KB Core (Server)"
        Tool_Search[Tool: search_knowledge]
        Tool_Context[Tool: build_rag_context]
        Resource_Raw[Resource: se-kb://files/...]
        Prompt_Gen[Prompt: generate_dfd]
        
        VectorDB[(向量数据库 Chroma)]
        FileSystem[(知识库 JSON 文件)]
        
        Tool_Search --> VectorDB
        Tool_Context --> VectorDB & FileSystem
        Resource_Raw --> FileSystem
    end
```

## 3. 详细实施路线图

### 第一阶段：MCP Server 能力升级 (Server Side)

**目标**：将现有的爬虫 Server 升级为全功能的知识库 Server。

1.  **集成向量检索 (Tools)**
    *   **`search_knowledge(query, intent, type)`**:
        *   功能：语义检索知识库。
        *   参数：支持按意图（Concept/Rule/Example）和类型过滤。
        *   实现：调用 `vectorizer.KnowledgeRetriever`。
    *   **`build_rag_context(task_description)`**:
        *   功能：智能组装 RAG 上下文。
        *   逻辑：一次性召回相关的"最佳实践"、"避坑指南(Rules)"和"模板"，直接返回适合 LLM 输入的格式化文本。

2.  **暴露知识资源 (Resources)**
    *   **`se-kb://concepts/{id}`**: 允许 Agent 直接读取特定概念的完整定义。
    *   **`se-kb://templates/{category}`**: 允许 Agent 获取标准模板结构。
    *   *价值*：Agent 可以通过 `read_resource` 获取精准的 JSON Schema 或原文，而不仅是搜索片段。

3.  **标准化提示词 (Prompts)**
    *   **`generate_dfd`**: 预设 Prompt，包含检索到的 DFD 规则和当前任务所需的模板。
    *   *价值*：让外部 Agent 一键获得"专家级"的 DFD 生成能力。

### 第二阶段：Web 接口适配 (Gateway Side)

**目标**：让 Web 界面具备"语义搜索"能力。

1.  **Web Client 改造**
    *   在 `web_client.py` 中新增路由 `/api/knowledge/search`。
    *   **关键点**：该接口不直接查库，而是通过 `MCPWebClient.session.call_tool("search_knowledge", ...)` 转发请求。保持 Web 端逻辑极简，复用 MCP 能力。

2.  **前端交互升级**
    *   新增 "知识库 (Knowledge Base)" 标签页。
    *   实现 "AI 搜索框"：用户输入自然语言（如"如何处理用户登录的数据流？"）。
    *   展示结果卡片：包含 匹配度(Score)、来源文件、知识类型标签。

### 第三阶段：生态互联 (Ecosystem)

**目标**：验证外部 Agent 调用能力。

1.  **Cursor/Claude 集成测试**
    *   配置 `claude_desktop_config.json` 或 Cursor MCP 设置，指向本地 `server.py`。
    *   验证场景：在 Cursor 中直接问 "@SE-KB 如何设计一个高并发的订单系统数据流图？"，验证其是否能自动调用 `search_knowledge` 并引用内部知识回答。

## 4. 技术栈调整

*   **Server**: Python `fastmcp`, `chromadb`, `vectorizer` (自研包)
*   **Web**: FastAPI (现有的 `web_client.py`), HTML/JS
*   **Protocol**: Model Context Protocol (MCP) v1.0

## 5. 预期成果

1.  **Web 用户**：获得一个带有语义理解能力的知识库搜索引擎。
2.  **Agent 开发者**：获得一个标准的 MCP 端点，可以即插即用，赋予通用 LLM "软件工程专家" 的领域知识。
3.  **系统维护**：只需维护一套核心逻辑 (MCP Server)，降低维护成本。
