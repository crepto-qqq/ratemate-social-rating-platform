# Template comments

The template detail page supports reading comments and posting, editing, or deleting your own comments when logged in. Comments belong to templates and are persisted in PostgreSQL. Guests can read them; writes require a session and CSRF token.

## Local startup

Run `docker compose exec -T backend python manage.py migrate` after updating the code, then open http://localhost:5173 and select a template from Discover. This adds migration `create_template.0006_comment`; existing data is preserved. The migration has already been applied in the current local environment.

## API

- `GET /api/templates/<id>/comments/?page=1`: newest first, 20 per page, `comments` and `hasMore`.
- `POST /api/templates/<id>/comments/`: JSON `{"content": "Your comment"}`.
- `PATCH /api/templates/<id>/comments/<comment_id>/`: same JSON; author only.
- `DELETE /api/templates/<id>/comments/<comment_id>/`: author only; empty 204 response.

Content is trimmed plain text, 1–2000 characters. Authors and permissions derive from the session. Comments display current author name/avatar, creation time, and an edited indicator. HTML is rendered as literal text. Invalid input returns 400, unauthenticated writes 401, other-user writes 403, and missing resources 404. Standard CSRF rejection returns 403.

Replies, comment notifications, moderation tools, and evaluation comments are outside this implementation.

## Verification (2026-10-11)

All 15 backend tests pass, including six comment test methods covering persistence, pagination, invalid input, ownership, missing resources, and CSRF. Frontend production build passes. Migration consistency and Git whitespace checks pass. Browser checks through Vite verified guest reads, pagination, posting literal HTML and multiline text, editing, persistence after refresh, cancellation and confirmation of deletion. Temporary verification records were removed.
