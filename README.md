# RateMate — 协作评分与个性化推荐平台

**Collaborative Rating and Recommendation Platform**

RateMate 是一个基于 Django、Vue 和 PostgreSQL 的全栈项目：用户可以创建评分模板、设置评价维度及权重、为条目评分，并通过公开评分、评论、点赞和收藏参与讨论。平台提供基于文本向量的个性化内容推荐、管理端内容审核和站内通知。

This is an authorised public copy of the University of Sydney ELEC3609 team project, published by **Tian Liao**. It contains the actual application source and its retained development history. Team and third-party contributions remain attributed to their respective authors.

## What the application does

- **Rating workflows:** reusable item/criterion templates, weighted scores, public/private results, template ownership and visibility controls.
- **Community interaction:** comments, favorites, likes and a notification inbox. The inbox is not a real-time chat system.
- **Account security:** email verification, email login codes, password reset, session authentication, CSRF protection, login throttling and image validation.
- **Moderation:** administrator actions, recorded reasons, audit records, and notifications to affected users.
- **Recommendations:** multilingual text embeddings, pgvector cosine retrieval and rule-based popularity/recency fallback. An asynchronous worker generates embeddings on CPU.
- **Optional AI ratings:** backend integration with OpenAI structured outputs, using the operator's own API key. This feature is separate from the locally computed recommendation embeddings.

## Stack and structure

| Layer | Implementation |
| --- | --- |
| Frontend | Vue 3, Vue Router, Vite, JavaScript and CSS |
| Backend | Python, Django, JSON APIs and database migrations |
| Storage | PostgreSQL 17 with pgvector; persistent media storage |
| Recommendation worker | FastEmbed / ONNX, multilingual MiniLM, 384-dimensional vectors |
| Local environment | Docker Compose, separate frontend/backend/worker, Mailpit for test email |

`backend/` contains the application, migrations and tests; `frontend/` contains the Vue application; `deploy/` contains historical security-update and verification tools; `docs/` contains design notes. Version pins and lockfiles are retained from the school source.

## Run locally

The supplied Compose configuration is for development. Install Docker with Compose, then from the repository root:

```powershell
Copy-Item .env.example .env
# Edit .env and set your own RATEMATE_DB_PASSWORD and DJANGO_SECRET_KEY.
docker compose up --build
```

On macOS/Linux, use `cp .env.example .env` for the first step. Do not overwrite an existing configuration.

- Application: <http://localhost:5173>
- Backend: <http://localhost:8000>
- Local verification/login emails: <http://localhost:8025>

The recommendation worker downloads its model on first use and caches it. The optional AI-rating feature needs a valid `OPENAI_API_KEY`; leave it empty if unused. Database migrations run during backend startup. No school database, user accounts, uploaded images or live service credentials are included.

See [DOCKER.md](DOCKER.md) for local setup and [RECOMMENDATIONS.md](RECOMMENDATIONS.md) for the ranking implementation and its limits. The deployment documents are historical engineering records; this publication does not assert that their server deployment was revalidated.

## Validation

See [docs/VALIDATION.md](docs/VALIDATION.md) for checks performed on this public export and environment limitations. The frontend has a build command but no automated test script. Full backend tests require PostgreSQL with pgvector; SQLite does not exercise vector SQL or PostgreSQL locking.

## Authorship and source

Tian's identifiable commits cover requirements documentation and the moderation/notification work, including administrator UI, backend authorization/audit handling, owner visibility flows and tests. Commit counts alone do not measure project management or the total amount of work; see [docs/CONTRIBUTIONS.md](docs/CONTRIBUTIONS.md) for evidence without assigning other members' work to one person.

- [Original school repository](https://github.sydney.edu.au/2026S2-INTERNET-SOFTWARE-PLATFORM/Fri-16-19-18) — school access may be required.
- Imported `main`: [`00955938e1fefadccc0d3a51d14e97085188eed4`](https://github.sydney.edu.au/2026S2-INTERNET-SOFTWARE-PLATFORM/Fri-16-19-18/commit/00955938e1fefadccc0d3a51d14e97085188eed4), dated 4 November 2026.
- Published snapshot: **14 November 2026**; 150 current source files and 62 retained source-history commits.
- [Source and refresh record](SOURCE_ORIGIN.md) · [Publication notice](NOTICE.md) · [Third-party notices](THIRD_PARTY_NOTICES.md)

This repository is a manually reviewed snapshot. It does **not** automatically synchronise with the school repository.
