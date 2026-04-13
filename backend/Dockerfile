# ==================== AI 数字员工后端服务 Dockerfile ====================
# 
# 基于 Python 3.11 slim 镜像构建
# 使用 uvicorn 作为 ASGI 服务器，支持多 worker 进程
#

# ==================== 基础镜像 ====================
# 使用 Python 3.11 slim 版本，体积小且包含必要的运行时
FROM python:3.11-slim

# ==================== 镜像元数据 ====================
LABEL maintainer="AI Digital Employee Team"
LABEL version="1.0.0"
LABEL description="AI 数字员工系统后端服务"

# ==================== 环境变量配置 ====================
# 防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1
# 禁用 Python 输出缓冲，确保日志实时输出
ENV PYTHONUNBUFFERED=1
# 设置工作目录环境变量
ENV APP_HOME=/app

# ==================== 系统依赖安装 ====================
# 安装必要的系统包（用于 asyncpg 等依赖的编译）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 用于 PostgreSQL 客户端库
    libpq-dev \
    # 用于编译 Python C 扩展
    gcc \
    # 用于 bcrypt 密码哈希
    libffi-dev \
    # 清理 apt 缓存，减小镜像体积
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ==================== 工作目录设置 ====================
WORKDIR ${APP_HOME}

# ==================== 依赖安装 ====================
# 先复制依赖文件，利用 Docker 缓存机制
# 只有 requirements.txt 变化时才重新安装依赖
COPY requirements.txt .

# 安装 Python 依赖
# --no-cache-dir 不缓存 pip 包，减小镜像体积
# --upgrade 确保安装最新兼容版本
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ==================== 应用代码复制 ====================
# 复制应用代码到容器
COPY . .

# ==================== 端口暴露 ====================
# 暴露 FastAPI 服务端口
EXPOSE 8000

# ==================== 健康检查 ====================
# 定期检查服务是否正常运行
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# ==================== 启动命令 ====================
# 使用 uvicorn 启动应用
# --host 0.0.0.0: 监听所有网络接口
# --port 8000: 监听 8000 端口
# --workers 4: 使用 4 个 worker 进程（利用多核 CPU）
# --proxy-headers: 信任代理头（用于获取真实客户端 IP）
# --forwarded-allow-ips "*": 允许所有转发 IP
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers", "--forwarded-allow-ips", "*"]
