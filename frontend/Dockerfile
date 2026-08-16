# 前端 React 容器：构建后由 Nginx 托管，并反向代理 /api 到后端
# 技术：Vite build + Nginx 静态托管 + 反向代理
# 基础镜像已预先从 DaoCloud 镜像源拉取到本地并 retag 为官方名称

# 阶段 1：构建
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
# 国内 npm 官方源经常断开，改用淘宝镜像
RUN npm config set registry https://registry.npmmirror.com && npm ci
COPY . .
RUN npm run build

# 阶段 2：运行
FROM nginx:alpine

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
