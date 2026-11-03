# RateMate A3 security update

This update preserves the two uWSGI backends and the existing AWS production settings.

## Application changes

- A database-backed login counter allows five attempts per username in ten minutes. PostgreSQL row locks share the limit across workers and containers. The counter stores a SHA-256 key, a count and the window start time.
- Uploaded avatars and template images are decoded with Pillow, limited to JPEG/PNG/WebP, 5 MiB input and 16 megapixels, and saved as newly encoded PNG pixels with random filenames. Supplied metadata and appended file content are removed.
- Moderation and rating-comment modifications check the existing verified-email and MFA session marker.
- Production 400/403/404/500 and CSRF failures return fixed JSON messages. Exception details remain in server logs.

## Deployment order

1. Back up the live PostgreSQL database and verify the archive.
2. Extract the security update archive into `/home/ubuntu/ratemate`.
3. Build `ratemate-backend:prod` using the existing `backend/Dockerfile.prod`.
4. Run migrations with `compose.prod.yaml` plus `compose.migrate.yaml`. The `migrate` service uses `ratemate_migrator`.
5. Apply `deploy/a3-security-permissions.sql` as the database administrator. This grants the runtime account the required operations on `accounts_loginthrottle`.
6. Recreate `backend_a` and `backend_b` without recreating the database.
7. Check login with OTP, template creation, images and comments. Run `python3 deploy/verify_login_limit.py` for a credential-free public endpoint check.

Keep `.env.prod` and the private credential files on the server. Do not put them in Git. Future schema migrations use the migration service; review runtime grants for new tables after migration.

## Nginx

`nginx-security.locations.conf` is an include for the existing server blocks. It rejects hidden files, application source paths, sensitive file extensions and active document types under `/media/`. Keep the existing `^~ /.well-known/acme-challenge/` location for certificate renewal. Validate the complete Nginx configuration before reloading it.

## Verification recorded on 4 November 2026

- Migration consistency check: no changes detected.
- SQLite business and security regressions: 78 tests passed.
- Isolated PostgreSQL 17 with pgvector: 96 tests passed, including recommendations and six concurrent login connections. Exactly five reservations succeeded and one was limited. Test password hashing was shortened only in the isolated test runner; production password hashing settings were unchanged.
- Live AWS checks and screenshots are collected after deployment.
