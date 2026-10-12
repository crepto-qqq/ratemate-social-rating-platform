# Template comments

## Scope

Implement comments in the existing template detail page, matching report FR2.7.1 and FR2.7.2. The current detail page already contains a Comments section. Comments belong to a Template, not a RatingResult. Evaluation comments would require a public evaluation detail page and separate access rules; that is outside this change.

## Behavior

- Anyone who can view the existing template detail page can read its comments.
- Authenticated users can post a plain text comment and edit or delete their own comments.
- Guests see a login link instead of a posting form. All write permissions are enforced in the backend.
- Show each author's current display name and avatar, content, creation time, and an edited indicator when applicable.
- Trim surrounding whitespace; reject empty content and content longer than 2000 characters.
- Fetch comments in pages of 20, ordered by creation time and ID descending. Provide a Load more action.
- Show loading, empty, error, and retry states. Preserve entered text after failed writes, disable duplicate submissions, and confirm deletion.
- Render content as text with preserved line breaks, without HTML interpretation.
- Replies, likes, moderation tools, notifications, and the Messages page remain separate work.

## Backend

Add a Comment model in create_template with Template and User_profile foreign keys, content, created_at, updated_at, and an index supporting template/order queries. Add an additive migration that preserves existing data.

GET/POST /api/templates/<template_id>/comments/ lists or creates comments. GET uses a validated positive page parameter and returns comments plus hasMore. PATCH/DELETE /api/templates/<template_id>/comments/<comment_id>/ updates or deletes a comment belonging to that template. Unauthenticated writes return 401, writes to another author's comment return 403, malformed JSON and invalid content return 400, missing resources return 404. Existing CSRF middleware and apiFetch token handling remain active. Ownership comes from the authenticated session, never client-provided author IDs.

## Frontend

Use a dedicated TemplateComments Vue component in the existing detail page. Load when template ID changes; discard stale responses and reset page state when navigating. Use existing apiFetch for all requests. Do not expose editable email addresses or other private account fields.

## Validation

Test persistence, listing/pagination, empty and oversized content, malformed JSON, anonymous write rejection, other-user edit/delete rejection, cross-template comment IDs, missing resources, and CSRF enforcement. Run the existing backend suite and frontend production build. Apply the migration to the running local database and inspect the integrated comment UI, including two-user permissions, without leaving demo records.

## Alternatives considered

1. Template comments: fits the current UI and report; recommended.
2. Evaluation comments: closer to result-specific discussion but requires a public result detail experience first.
3. Comments on both: broader functionality but duplicates interface and permissions work before evaluation discovery is available.

## Approval

User approved local implementation on 2026-10-11. Implemented and verified; see docs/template-comments.md.
