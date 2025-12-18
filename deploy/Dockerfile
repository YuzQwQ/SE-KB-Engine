# 使用官方轻量级 Python 镜像
FROM python:3.10-slim

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (编译工具和常用库)
# ChromaDB 可能需要 g++ 编译
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements-prod.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements-prod.txt

# 复制应用代码
COPY api/ ./api/
COPY vectorizer/ ./vectorizer/
COPY se_kb/ ./se_kb/
# 注意：不复制 web/, scripts/ 等离线/前端代码，减小体积

# 创建日志目录
RUN mkdir -p logs

# 创建非 root 用户运行
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 暴露端口
EXPOSE 8000

# 启动命令
# 4 个 Worker，绑定 0.0.0.0:8000，超时 120秒（防止大模型生成慢）
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "api.app:app"]
