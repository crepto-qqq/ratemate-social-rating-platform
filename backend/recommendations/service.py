import hashlib
import json
import math
import time
from datetime import timedelta

from django.db.models import Count, F, Q
from django.utils import timezone
from pgvector.django import CosineDistance

from create_template.models import Favorite, Template
from rating.models import RatingResult, RatingResultLike
from .embedding import MODEL, normalized
from .models import TemplateEmbedding, UserPreference

CACHE_SECONDS = 600
MAX_CANDIDATES = 50

def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()

def completed_results(queryset):
    return queryset.annotate(
        n_items=Count('template__items', distinct=True),
        n_criteria=Count('template__criteria', distinct=True),
        n_scores=Count('scores', distinct=True),
    ).filter(n_items__gt=0, n_criteria__gt=0, n_scores=F('n_items') * F('n_criteria'))

def interest_weights(user):
    if user is None:
        return {}
    weights = {}
    def add(ids, weight):
        for template_id in ids:
            weights[template_id] = max(weights.get(template_id, 0), weight)
    add(Template.objects.filter(owner=user).values_list('id', flat=True), 1)
    # Auto-favorites of authored templates must not become a second, stronger vote.
    add(Favorite.objects.filter(user=user).exclude(template__owner=user).values_list('template_id', flat=True), 2)
    add(completed_results(RatingResult.objects.filter(owner=user)).values_list('template_id', flat=True), 2)
    liked = RatingResult.objects.filter(is_public=True, likes__user=user).exclude(owner=user)
    add(completed_results(liked).values_list('template_id', flat=True), 3)
    return weights

def preference(user, weights):
    if user is None:
        return None, 'guest'
    sources = list(TemplateEmbedding.objects.filter(
        template_id__in=weights, status='ready', model=MODEL, vector__isnull=False,
    ).order_by('template_id'))
    source_key = fingerprint({'weights': weights, 'sources': [
        (source.template_id, source.content_hash, str(source.updated_at), source.model) for source in sources]})
    stored = UserPreference.objects.filter(user=user).first()
    if stored and stored.fingerprint == source_key:
        return (None if stored.vector is None else list(stored.vector)), source_key
    combined = [0.0] * 384
    for source in sources:
        for index, value in enumerate(source.vector):
            combined[index] += float(value) * weights[source.template_id]
    vector = normalized(combined)
    UserPreference.objects.update_or_create(user=user, defaults={'vector': vector, 'fingerprint': source_key})
    return vector, source_key

def metadata(kind, user):
    if kind == 'templates':
        queryset = Template.objects.all()
        if user:
            queryset = queryset.exclude(owner=user)
        return list(queryset.annotate(
            heat=Count('favorite_records', filter=~Q(favorite_records__user_id=F('owner_id')), distinct=True)
        ).values('id', 'heat', 'created_at', 'updated_at').order_by('id'))
    queryset = completed_results(RatingResult.objects.filter(is_public=True))
    if user:
        queryset = queryset.exclude(owner=user).exclude(likes__user=user)
    return list(queryset.annotate(heat=Count('likes', distinct=True)).values('id', 'template_id', 'heat', 'created_at').order_by('id'))

def freshness(date, now):
    age_days = max(0, (now - date).total_seconds() / 86400)
    return math.exp(-age_days / 30)

def recommend(request, kind, user):
    weights = interest_weights(user)
    vector, preference_key = preference(user, weights)
    rows = metadata(kind, user)
    template_ids = [row['id'] if kind == 'templates' else row['template_id'] for row in rows]
    embedding_meta = list(TemplateEmbedding.objects.filter(template_id__in=template_ids).order_by('template_id').values(
        'template_id', 'status', 'model', 'content_hash', 'updated_at'))
    key = fingerprint({'algorithm': 1, 'kind': kind, 'user': user.pk if user else None,
                       'preference': preference_key, 'weights': weights, 'rows': rows, 'embeddings': embedding_meta})
    cache_name = 'discover_recommendations_' + kind
    cached = request.session.get(cache_name)
    if cached and cached.get('key') == key and time.time() - cached.get('generated', 0) < CACHE_SECONDS:
        return cached['ids'], cached['reasons'], cached['personalized']
    now = timezone.now()
    heat_max = max((math.log1p(row['heat']) for row in rows), default=0) or 1
    trending = sorted(rows, key=lambda row: (
        .65 * math.log1p(row['heat']) / heat_max + .35 * freshness(row['created_at'], now), row['id']), reverse=True)
    selected_ids = set(row['id'] for row in trending[:20])
    selected_ids.update(row['id'] for row in sorted(rows, key=lambda row: row['created_at'], reverse=True)[:20])
    distances = {}
    if vector is not None:
        nearest = list(TemplateEmbedding.objects.filter(
            template_id__in=template_ids, status='ready', model=MODEL, vector__isnull=False,
        ).annotate(distance=CosineDistance('vector', vector)).order_by('distance', 'template_id')[:MAX_CANDIDATES])
        distances = {entry.template_id: float(entry.distance) for entry in nearest}
        if kind == 'templates':
            selected_ids.update(distances)
        else:
            selected_ids.update(row['id'] for row in rows if row['template_id'] in distances)
    scored = []
    reasons = {}
    personalized = vector is not None and bool(distances)
    for row in rows:
        if row['id'] not in selected_ids:
            continue
        template_id = row['id'] if kind == 'templates' else row['template_id']
        similarity = max(0, min(1, 1 - distances.get(template_id, 1)))
        popularity = math.log1p(row['heat']) / heat_max
        recency = freshness(row['created_at'], now)
        score = (.75 * similarity + .15 * popularity + .10 * recency) if personalized else (.65 * popularity + .35 * recency)
        # Reusing the same template is less useful than discovering an unseen one.
        if kind == 'templates' and template_id in weights:
            score *= .6
        reasons[str(row['id'])] = 'Based on your interests' if personalized and similarity > .3 else ('Popular in the community' if row['heat'] else 'Recently shared')
        scored.append((score, row['created_at'], row['id'], template_id))
    scored.sort(reverse=True)
    # Round-robin over templates limits one topic from filling the first screen.
    ordered, remaining, seen_templates = [], [], set()
    for entry in scored:
        if entry[3] in seen_templates:
            remaining.append(entry[2])
        else:
            ordered.append(entry[2])
            seen_templates.add(entry[3])
    ordered.extend(remaining)
    request.session[cache_name] = {
        'key': key, 'generated': time.time(), 'ids': ordered, 'reasons': reasons, 'personalized': personalized}
    return ordered, reasons, personalized
