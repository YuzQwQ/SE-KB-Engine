# SE-KB 知识服务 API 部署方案 (修订版)

本文档基于“知识基础设施化”的原则，对原设计方案进行了修订。核心目标是将现有的高质量知识库封装为**可靠、低延迟、跨网络可调用**的标准服务，供 DFD 生成 Agent 等下游系统使用。

---

## 1. 设计原则与调整

根据最新的工程建议，我们对系统边界进行了重新划分：

*   **聚焦核心价值**：对外 API 的核心职责是 **"向量检索 + 结构化知识返回" (RAG)**。这是高频、低延迟的在线需求。
*   **离线/在线分离**：
    *   **Online (API 服务)**：轻量级、高稳定性。**不依赖 Tor**，不执行耗时的爬取/精炼任务。只负责读取向量索引响应查询。
    *   **Offline (数据维护)**：爬虫、知识精炼、向量索引构建。这些作为**离线任务**或**内部脚本**运行，不直接通过公网 API 暴露，避免阻塞在线服务或引入不稳定因素。
*   **基础设施化**：保留 Docker、Gunicorn、Nginx、API Key 鉴权，确保跨网络调用的安全性和标准化。

---

## 2. 系统架构设计 (Online/Offline 分离)

```mermaid
graph TD
    User[下游 Agent / 远程系统] -->|HTTPS + API Key| Nginx[Nginx 网关]
    Nginx -->|Read-Only 请求| APIService[API 服务容器 (Gunicorn)]
    
    subgraph "Online Zone (高可用)"
        APIService -->|读取| VectorDB[向量索引 (se_kb/vector_store)]
        APIService -->|调用| LLM[SiliconFlow API (仅用于 Embedding)]
    end
    
    subgraph "Offline Zone (内部维护)"
        Crawler[爬虫/精炼脚本] -->|SOCKS5| Tor[Tor 代理]
        Crawler -->|写入| RawData[原始数据]
        Refiner[精炼/构建脚本] -->|写入| VectorDB
    end
    
    RawData -.-> Refiner
```

### 关键变化
1.  **API 服务解耦**：API 容器**不再**连接 Tor 代理，移除了对不稳定外部网络的依赖，只专注于查库。
2.  **数据流单向性**：离线任务负责写入/更新向量库，在线 API 服务只负责读取（支持热重载）。

---

## 3. API 接口定义 (精简版)

对外暴露的 API 仅包含核心检索能力和必要的系统状态检查。

### 3.1 核心服务接口 (Public)

| 方法 | 路径 | 描述 | 关键参数 |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/search` | **语义检索 (RAG)** | `query` (查询词), `intent` (意图: concept/rule/example...), `top_k` |
| `GET` | `/api/v1/health` | **健康检查** | 无 (返回服务存活状态，用于监控) |

### 3.2 管理接口 (Admin Only / Internal)

*建议通过内网访问或配置严格的 IP 白名单/Admin Key*

| 方法 | 路径 | 描述 | 场景 |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/admin/reload` | **索引热重载** | 离线任务更新索引后，通知 API 服务重新加载 |
| `GET` | `/api/v1/admin/stats` | **知识库统计** | 查看当前索引覆盖率和文档数 |

*(注：爬取 `/crawl` 和精炼 `/refine` 接口建议从对外 API 中移除，改为通过服务器后台 CLI 脚本触发，或者仅在开发环境 Web UI 中保留)*

---

## 4. 容器化部署方案

### 4.1 目录结构调整
```text
mcp-client/
├── api/                 # [核心] 在线 API 服务代码
│   ├── v1/
│   │   ├── search.py    # 检索逻辑
│   │   └── admin.py     # 管理逻辑
│   ├── auth.py          # API Key 鉴权
│   └── app.py           # Gunicorn 入口
├── scripts/             # [离线] 维护脚本 (爬虫、构建索引)
├── se_kb/               # [数据] 挂载目录
├── deploy/              # 部署配置
│   ├── docker-compose.yml
│   └── nginx.conf
└── requirements.txt     # 生产环境依赖 (不含爬虫复杂依赖)
```

### 4.2 `docker-compose.yml` (在线服务版)

生产环境仅需启动在线服务部分：

```yaml
version: '3.8'

services:
  # 核心 API 服务
  kb-api:
    build: 
      context: .
      dockerfile: deploy/Dockerfile
    image: se-kb-api:v1
    restart: always
    environment:
      - FLASK_ENV=production
      - WORKERS=4
    volumes:
      - ./se_kb:/app/se_kb:ro    # 只读挂载知识库，防止意外修改
      - ./logs:/app/logs
      - ./.env:/app/.env
    ports:
      - "8000:8000"

  # Nginx 网关
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./deploy/nginx.conf:/etc/nginx/nginx.conf
      - ./deploy/certs:/etc/nginx/certs
    depends_on:
      - kb-api
```

---

## 5. 实施路线图

1.  **代码层 (API 模块)**
    *   新建 `api/` 目录，将 `KnowledgeRetriever` 封装为标准的 Flask API。
    *   实现 API Key 鉴权中间件。
    *   移除 API 服务代码中对爬虫模块 (`WebpageCrawler`) 的依赖引用。

2.  **配置层 (依赖精简)**
    *   创建 `requirements-prod.txt`，排除 Playwright、Tor 控制库等仅爬虫需要的依赖，大幅减小镜像体积。

3.  **部署层 (Docker)**
    *   编写 Dockerfile，构建仅包含检索服务的轻量级镜像。
    *   配置 Nginx 反向代理与 SSL。

4.  **运维流程**
    *   **更新知识库流程**：
        1. 在开发机/离线服务器运行爬虫和精炼脚本。
        2. 生成新的向量索引 (`se_kb/vector_store`)。
        3. 将新索引同步到生产服务器 (rsync/scp)。
        4. 调用 `/api/v1/admin/reload` 热加载新索引。

---

## 6. 总结

本方案将系统明确划分为**在线查询**与**离线生产**两部分。对外提供的 API 仅聚焦于**提供稳定的知识检索服务**，剥离了不稳定的爬取和复杂的精炼过程。这不仅降低了系统的耦合度和运维风险，也完全符合跨网络基础设施调用的设计初衷。
