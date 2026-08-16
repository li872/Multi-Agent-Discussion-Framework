# 前端 React 容器：构建后由 Nginx 托管，并反向代理 /api 到后端
# 技术：Vite build + Nginx 静态托管 + 反向代理
# 使用阿里云镜像源，避免国内拉取 docker.io 官方镜像失败

# 阶段 1：构建
FROM registry.cn-hangzhou.aliyuncs.com/library/node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# 阶段 2：运行
FROM registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine

# Nginx 配置：托管 dist/，并把 /api 反向代理到后端服务
RUN cat > /etc/nginx/conf.d/default.conf <<'EOF'
server {
    listen 80;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # 关闭缓冲，保证 SSE 流式正常
    proxy_buffering off;
    proxy_cache off;
    chunked_transfer_encoding on;

    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Connection '';
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
