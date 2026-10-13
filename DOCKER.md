# Docker 本地开发

Vue 3 + Vite 使用 Node 22；Django 使用 Python 3.13；数据库使用 PostgreSQL 17。
本配置启用热更新，使用开发服务器和 DEBUG=True。

## 启动

启动 Docker Desktop，在 Settings > Resources > WSL Integration 启用 Ubuntu。
在 WSL 的项目根目录执行：

```bash
cp .env.example .env
# 编辑根目录 .env，修改 RATEMATE_DB_PASSWORD
docker compose up --build
```

PowerShell 复制文件使用 `Copy-Item .env.example .env`。
浏览器访问 http://localhost:5173；后端端口为 http://localhost:8000。
注册及登录验证码默认发送到本地 Mailpit，打开 http://localhost:8025 查看邮件。
注册时需输入邮箱并验证；此后每次登录仍需输入邮件验证码。
旧账号首次登录需绑定并验证邮箱。
数据库健康检查通过后，后端自动 migrate 并启动。
这是新的独立数据库，不会自动导入本机原有数据。

## 文件与连接

- backend/Dockerfile 安装 Python 依赖，frontend/Dockerfile 使用 npm ci 安装锁定依赖。
- compose.yaml 编排四个容器；后端通过 db:5432 连接数据库，通过 mailpit:1025 发送本地测试邮件。
- 根目录 .env 供 Compose 使用，backend/.env 仍可供非 Docker 开发使用。
- 前端 VITE_API_BASE_URL 为空，请求同源 /api，由 Vite 代理至 backend:8000。
- 代理保留浏览器 Host，返回的图片 URL 通过 /media 代理访问。
- 源码挂载支持热更新；数据库、上传图片和 node_modules 使用独立数据卷。
- PostgreSQL 密码仅在数据卷首次初始化时设置，之后修改 .env 不会修改数据库用户密码。

## 真实 QQ 邮件

在 QQ 邮箱中启用 SMTP 服务并生成授权码，修改根目录被 Git 忽略的 .env：

```dotenv
EMAIL_HOST=smtp.qq.com
EMAIL_PORT=465
EMAIL_USE_SSL=true
EMAIL_USE_TLS=false
EMAIL_HOST_USER=user-63aebf0e1dd0@example.invalid
EMAIL_HOST_PASSWORD=your-qq-smtp-authorization-code
DEFAULT_FROM_EMAIL=user-63aebf0e1dd0@example.invalid
```

运行 `docker compose up -d --force-recreate backend` 使配置生效。授权码只填在本机 .env，不要提交到仓库或发到聊天中。

## 常用操作

```bash
docker compose up -d --build
docker compose logs -f backend
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose down
```

`down` 保留数据；`down -v` 会删除数据库、图片和前端依赖卷。
修改前端依赖后执行：

```bash
docker compose build frontend
docker compose run --rm --no-deps frontend npm ci
docker compose up -d
```

本配置用于本地开发。正式部署需另配前端静态服务器、生产 WSGI/ASGI 服务、DEBUG=False 和密钥。
