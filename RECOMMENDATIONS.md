# Discover recommendations

Discover keeps Community ratings as its first tab and Templates as its second.
For you is the default order; Latest retains chronological browsing. Search uses
the existing text search rather than mixing personal interests into relevance.

## Local setup

```bash
docker compose up -d --build
docker compose logs -f embeddings
```

The database image includes pgvector and remains PostgreSQL 17. The original
postgres_data volume is retained. New migrations add the vector extension,
TemplateEmbedding and UserPreference. Never remove the database volume to enable
recommendations.

A separate embeddings worker downloads and runs
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 with FastEmbed/ONNX on
CPU. It produces normalized 384-dimensional vectors and supports Chinese and
English. Model files are cached in the embedding_models volume. Template text is
processed locally; no paid API key or remote inference is needed. Downloads need
internet access on first use. The first request never downloads a model.

Templates are saved immediately, then queued for encoding. Existing templates
are queued by migration. Content changes invalidate their vectors; failures are
retried after five minutes. A job token prevents publishing vectors for obsolete
content. A ten-minute lease recovers interrupted processing.

```bash
# Run once, or regenerate every template after changing the model/input format:
docker compose exec embeddings python manage.py embed_templates --rebuild
```

For non-Docker installations, install requirements.txt, install the PostgreSQL
vector extension, run migrations and run `python manage.py embed_templates --watch`
as a separate process. Set EMBEDDING_CACHE_DIR to a writable cache directory.

## Interest signals

Template text combines title, description, criterion names and item names. User
names, email addresses, comments and star scores are excluded. This first version
does not introduce tags or infer preferences from images.

Each user/template pair gets one weight, taking the strongest available signal:

| Signal | Weight |
| --- | --- |
| Creating a template | 1 |
| Manually favoriting another user's template | 2 |
| Completing a rating, public or private | 2 |
| Liking another user's complete public rating | 3 |

The creation auto-favorite is not counted separately. Repeated ratings or liking
multiple results for the same template does not multiply the signal. Item star
values are not treated as liking the topic. A normalized weighted sum of ready
template vectors becomes the user's preference vector.

Current database relationships are checked on each recommendation request.
Unfavorites, unlikes, deleted ratings and visibility changes therefore affect the
next feed request. Private rating history can inform its owner's preferences,
but private results are never recommendation candidates.

## Ranking and caching

pgvector performs exact cosine-distance retrieval for up to 50 template candidates.
Popular and recent candidates supplement retrieval. Candidate scores combine:

- 75% semantic similarity, 15% normalized log popularity, 10% recency.
- Without a usable preference vector: 65% popularity, 35% recency.
- Recency decays exponentially with a 30-day time constant.

Template popularity excludes favorites from the template's creator. Public rating
popularity uses its likes. Authored content is excluded from personalized feeds;
already liked results are excluded, and saved/rated templates are demoted. Latest
still shows the user's own published content and templates. Results from different
templates are placed first to avoid one template filling the first screen.

Session caches hold ordered IDs and reasons for ten minutes. A fingerprint covers
feedback, eligible content, heat and vector versions; changes bypass the cached
order. Public visibility is checked again during serialization. Recommendation
weights are initial rules, not an evaluated optimal configuration.

## API and limits

`GET /api/recommendations/?kind=ratings|templates&page=1`

Returns results/templates, hasMore and personalized. Cards include a short
recommendationReason. Pages contain up to 20 entries. Guests receive the popular/
recent fallback; an empty pool shows an empty state with access to Latest.

This version targets the current small dataset. Feedback and eligible-content
metadata are checked synchronously; only encoding is asynchronous. At larger
scale, move invalidation to version counters/events and measure latency before
adding approximate vector indexes. No collaborative filtering or click tracking
is implemented.
