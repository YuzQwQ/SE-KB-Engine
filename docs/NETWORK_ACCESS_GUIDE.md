# 网络访问指南：如何让外部系统调用您的 API

本文档介绍了三种将本地 SE-KB 知识库服务暴露给公网（外部网络）的方法。

---

## 方案一：Cloudflare Tunnel (推荐 - 免费/安全/HTTPS)

这是目前最推荐的本地服务暴露方式，它不需要您拥有公网 IP，也不需要配置路由器，且自带 HTTPS 支持。

### 方法 A：使用临时隧道 (无需账号，测试用)
如果您只是想快速让别人测试一下，可以使用临时隧道。

1. **下载 cloudflared**
   - Windows 下载地址: [cloudflared-windows-amd64.exe](https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe)
   - 将其重命名为 `cloudflared.exe` 并放在项目根目录。

2. **启动隧道**
   在终端运行（确保您的 API 服务已在 8000 端口启动）：
   ```powershell
   .\cloudflared.exe tunnel --url http://localhost:8000
   ```

3. **获取公网地址**
   终端会输出类似如下的日志：
   ```text
   +--------------------------------------------------------------------------------------------+
   |  Your quick Tunnel has been created! Visit it at (it may take some time to be reachable):  |
   |  https://random-name-1234.trycloudflare.com                                              |
   +--------------------------------------------------------------------------------------------+
   ```
   **`https://random-name-1234.trycloudflare.com`** 就是您的公网 API 地址！
   
   外部调用示例：
   ```bash
   POST https://random-name-1234.trycloudflare.com/api/v1/search
   Authorization: Bearer <your-key>
   ```

### 方法 B：使用持久化隧道 (Docker 集成)
如果您有自己的域名并托管在 Cloudflare，可以在 `docker-compose.yml` 中配置持久化隧道。

1. 在 [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) 面板创建 Tunnel。
2. 获取 `TUNNEL_TOKEN`。
3. 在 `deploy/docker-compose.yml` 中取消 `tunnel` 服务的注释并填入 Token。

---

## 方案二：内网穿透工具 (cpolar / ngrok)

适合没有域名且不想配置 Cloudflare 的用户。

### 使用 cpolar (国内访问速度较快)
1. 注册并下载 [cpolar](https://www.cpolar.com/)。
2. 启动 API 服务。
3. 运行映射命令：
   ```powershell
   cpolar http 8000
   ```
4. 复制生成的公网地址 (如 `http://xyz.cpolar.io`) 给调用方。

---

## 方案三：云服务器部署 (生产环境标准)

如果您决定正式上线，建议购买一台云服务器 (VPS)。

1. **购买服务器**: 推荐 Ubuntu 22.04 LTS。
2. **安装 Docker**:
   ```bash
   curl -fsSL https://get.docker.com | bash
   ```
3. **上传代码**:
   使用 `scp` 或 `git` 将项目代码同步到服务器。
4. **启动服务**:
   ```bash
   # 在服务器上执行
   cd mcp-client
   docker compose -f deploy/docker-compose.yml up -d --build
   ```
5. **访问**: 直接使用 `http://<服务器公网IP>:80` 访问。

---

## 常见问题

### Q: 外部访问 API 报错 403 Forbidden?
**A:** 检查请求头是否包含了正确的 API Key。
```http
Authorization: Bearer sk-read-key...
```
并且确保 `docker-compose.yml` 或环境变量中配置了对应的 `KB_READ_KEYS`。

### Q: 隧道连接不稳定？
**A:** 临时隧道（Quick Tunnel）可能会在 24 小时后过期或因网络波动断开。长期使用建议使用 **方案三 (云服务器)** 或 **方案一的方法 B (持久化隧道)**。
