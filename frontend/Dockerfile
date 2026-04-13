# ==================== AI 数字员工前端服务 Dockerfile ====================
#
# 多阶段构建：
# Stage 1: Node.js 构建前端静态文件
# Stage 2: Nginx 提供静态文件服务
#

# ==================== Stage 1: 构建阶段 ====================
# 使用 Node.js 18 Alpine 版本作为构建环境
FROM node:18-alpine AS builder

# 镜像元数据
LABEL stage="builder"
LABEL description="前端构建阶段"

# 设置工作目录
WORKDIR /app

# 设置 npm 镜像源（可选，加速国内构建）
# RUN npm config set registry https://registry.npmmirror.com

# 复制 package.json 和 package-lock.json（利用 Docker 缓存）
COPY package*.json ./

# 安装依赖
# --frozen-lockfile 确保使用 lock 文件中的精确版本
# --production=false 安装所有依赖（包括 devDependencies）
RUN npm ci --legacy-peer-deps && npm install terser

# 复制源代码
COPY . .

# 构建生产版本
# Vite 会生成优化后的静态文件到 dist 目录
RUN npm run build


# ==================== Stage 2: 生产阶段 ====================
# 使用 Nginx Alpine 版本作为生产服务器
FROM nginx:1.25-alpine AS production

# 镜像元数据
LABEL maintainer="AI Digital Employee Team"
LABEL version="1.0.0"
LABEL description="AI 数字员工系统前端服务"

# ==================== 安全配置 ====================
# 移除默认的 Nginx 配置
RUN rm -rf /etc/nginx/conf.d/default.conf

# ==================== 复制配置文件 ====================
# 复制自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ==================== 复制构建产物 ====================
# 从构建阶段复制静态文件到 Nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# ==================== 权限设置 ====================
# 确保 Nginx 可以读取静态文件
RUN chmod -R 755 /usr/share/nginx/html

# ==================== 端口暴露 ====================
# 暴露 HTTP 端口
EXPOSE 80

# ==================== 健康检查 ====================
# 定期检查 Nginx 服务是否正常
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# ==================== 启动命令 ====================
# 以前台模式启动 Nginx
# daemon off 确保进程在前台运行，容器不会立即退出
CMD ["nginx", "-g", "daemon off;"]
