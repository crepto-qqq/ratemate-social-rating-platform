# Docker 本地开发

> 公开副本说明：本文中的 `user-...@example.invalid` 是脱敏占位地址，不能用于发信；请在所有相关配置中填写自己的发件账号。学校共用邮箱和凭据未公开。根目录 `.env` 还应设置自己的 `DJANGO_SECRET_KEY`；不使用 AI 评分时，将 `OPENAI_API_KEY` 留空。

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

以下步骤适用于**运行 Django 后端的电脑或服务器**。请使用自己有权管理的 Gmail 发件账号；下文的 `your-sender@example.com` 仅为占位地址，必须替换。注册用户填写的是自己的收件邮箱。每个独立后端需要单独配置发件服务。

1. 发件邮箱的管理者登录自己的 Gmail 账号，在 [Google 账号安全设置](https://myaccount.google.com/security)中开启两步验证，并在[应用专用密码页面](https://myaccount.google.com/apppasswords)为 RateMate 生成应用专用密码。若页面不支持生成，检查账号的两步验证状态和页面给出的限制。`EMAIL_HOST_PASSWORD` **不能填平时登录 Gmail 的密码**。
2. 在项目根目录（`compose.yaml` 所在目录）创建 `.env`。PowerShell 可运行 `Copy-Item .env.example .env`；如果 `.env` 已存在，直接编辑现有文件，不要覆盖原来的 `RATEMATE_DB_PASSWORD`。把邮件相关的行改成下面这样：

```dotenv
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_SSL=false
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your-sender@example.com
EMAIL_HOST_PASSWORD=your-google-app-password
DEFAULT_FROM_EMAIL=your-sender@example.com
```

3. 将 `EMAIL_HOST_USER` 和 `DEFAULT_FROM_EMAIL` 中的占位地址都替换为自己的 Gmail 发件地址，将 `your-google-app-password` 替换为 **Google 应用专用密码**。如果 Google 展示密码时用空格分组，填入 `.env` 时去掉这些空格。其余服务器与端口配置可照抄，不要在值外额外加引号。
4. 保存 `.env`，在项目根目录运行 `docker compose up -d --force-recreate backend`，让后端重新读取配置。前端仍访问 http://localhost:5173。
5. 用**另一个邮箱地址**注册测试。验证码应该到注册时填写的收件箱（必要时检查垃圾邮件），而不是 http://localhost:8025 的 Mailpit。忘记密码和登录验证码也使用同一发件配置。

如果邮件仍进 Mailpit，检查是否编辑了**项目根目录**的 `.env`、`EMAIL_HOST` 是否为 `smtp.gmail.com`，以及后端是否已经重新创建。如果发送失败，可运行 `docker compose logs --tail=100 backend` 查看错误，但不要把包含凭据的日志直接公开。

`.env` 已被 Git 忽略，不要把它提交到仓库。队友如果改用自己的 Gmail 发件账号，应将 `EMAIL_HOST_USER`、`DEFAULT_FROM_EMAIL` 和应用专用密码一起改为自己的。尚未取得应用专用密码时，保持 `.env.example` 的 Mailpit 配置，即可在 http://localhost:8025 测试邮件。

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
