# Template Comments Implementation Plan

**Goal:** Add persistent template comments to the existing detail page locally.
**Architecture:** A Comment model and session-authorized Django endpoints serve a dedicated Vue component using apiFetch. Existing Docker volumes provide hot reload.
**Tech Stack:** Django, PostgreSQL, Vue 3, Vite.

## Constraints

Template comments only; plain text, 1–2000 trimmed characters; 20 comments per page; only authors can edit/delete; retain CSRF protection; no messages or notifications.

## Tasks

- [x] Write `backend/create_template/test_comments.py` for persistence, guest reads, author permissions, invalid payloads, pagination, missing/cross-template resources, and CSRF protection. Run `docker compose exec -T backend python manage.py test create_template.test_comments` and confirm missing endpoint failures.
- [x] Add Comment in `backend/create_template/models.py`, endpoints in `comment_views.py`, and routes in `urls.py`. Generate additive migration using `python manage.py makemigrations create_template`. Rerun new tests and the full backend suite.
- [x] Add `frontend/src/components/TemplateComments.vue`; mount it in `TemplateDetailPage.vue`. Handle pagination, stale responses, guest login links, edit/delete, loading/retry, and preserved input on failure. Run `docker compose exec -T frontend npm run build`.
- [x] Apply migration with `docker compose exec -T backend python manage.py migrate`; inspect browser interactions and Vite proxy responses. Review permission handling, run `git diff --check`, and document verification. Leave changes local for user review.

User approved local implementation on 2026-10-11. Work remains in the existing checkout on codex/template-comments so the running local Docker bind mounts show changes.
