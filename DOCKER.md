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
登录页的 Forgot password? 可向已验证邮箱发送 5 分钟有效的重置码，输入验证码和新密码后重新登录。
旧账号首次登录需绑定并验证邮箱。
数据库健康检查通过后，后端自动 migrate 并启动。
这是新的独立数据库，不会自动导入本机原有数据。

## 文件与连接

- backend/Dockerfile 安装 Python 依赖，frontend/Dockerfile 使用 npm ci 安装锁定依赖。
- compose.yaml 编排数据库、后端、前端、Mailpit 和推荐向量后台服务；后端通过 db:5432 连接数据库，默认通过 mailpit:1025 发送本地测试邮件。
- 根目录 .env 供 Compose 使用，backend/.env 仍可供非 Docker 开发使用。
- 前端 VITE_API_BASE_URL 为空，请求同源 /api，由 Vite 代理至 backend:8000。
- 代理保留浏览器 Host，返回的图片 URL 通过 /media 代理访问。
- 源码挂载支持热更新；数据库、上传图片和 node_modules 使用独立数据卷。
- PostgreSQL 密码仅在数据卷首次初始化时设置，之后修改 .env 不会修改数据库用户密码。

## 真实 Gmail 邮件

以下步骤适用于**运行 Django 后端的电脑或服务器**。用户注册时可以填写自己的任意有效收件邮箱；`user-f16e10456aac@example.invalid` 是发件邮箱，不是每个用户都要拥有的邮箱。每位队友各自运行本地后端时，配置不会自动同步；共用部署只需在共用后端配置一次。

1. 登录发件邮箱对应的 Google 账号，前往 [Google 账号安全设置](https://myaccount.google.com/security)开启两步验证，然后在[应用专用密码页面](https://myaccount.google.com/apppasswords)为 RateMate 生成应用专用密码。如果此功能不可用，先检查账号的两步验证及 Google 给出的账号限制。**日常登录 Gmail 的密码不能填入 `EMAIL_HOST_PASSWORD`。**
2. 在项目根目录将 `.env.example` 复制为 `.env`（PowerShell：`Copy-Item .env.example .env`；若 `.env` 已存在，直接编辑它，不要覆盖原有数据库密码）。将下面的邮件配置写进根目录 `.env`，把尖括号中的占位文字替换为新生成的应用专用密码；复制时去掉 Google 为便于阅读而显示的空格：

```dotenv
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_SSL=false
EMAIL_USE_TLS=true
EMAIL_HOST_USER=user-f16e10456aac@example.invalid
EMAIL_HOST_PASSWORD=<Google 应用专用密码，不是 Gmail 登录密码>
DEFAULT_FROM_EMAIL=user-f16e10456aac@example.invalid
```

3. 在项目根目录运行 `docker compose up -d --force-recreate backend`，让后端重新读取配置。用另一个收件邮箱注册测试；验证码应送到该邮箱（必要时检查垃圾邮件），而不是 Mailpit。

如果邮件仍进 Mailpit，检查是否编辑了**项目根目录**的 `.env`、`EMAIL_HOST` 是否为 `smtp.gmail.com`，以及后端是否已经重新创建。如果发送失败，可运行 `docker compose logs --tail=100 backend` 查看错误，但不要把包含凭据的日志直接公开。

应用专用密码只保存在运行后端的环境中，不要提交 `.env` 到仓库，也不要把 Gmail 登录密码或应用专用密码发到聊天中。队友若在自己的电脑上使用另一个 Gmail 发件账号，需要把上面的两个邮箱地址改成自己的账号，并生成自己的应用专用密码。尚未取得应用专用密码时，保持 `.env.example` 的 Mailpit 配置，即可在 http://localhost:8025 测试邮件。

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

## 推荐系统

数据库现使用支持 pgvector 的 PostgreSQL 17 镜像，继续复用原有数据卷。
运行 `docker compose up -d --build` 会执行迁移，并启动 `embeddings` 后台服务。
首次运行需下载多语言模型，随后在本机 CPU 上生成模板向量；模型下载或生成暂时失败时，首页使用热门与最近内容。
模型文件保存在 `embedding_models` 卷中。不要使用 `down -v` 来升级推荐系统，它会删除数据库和其他数据卷。
实现规则及维护命令见 [RECOMMENDATIONS.md](RECOMMENDATIONS.md)。
