import json

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from accounts.profiles import current_profile
from create_template.models import Template
from notifications.services import remove_interaction_notifications

from .models import RatingResult, RatingScore


def _current_owner(request):
    return current_profile(request)


def _read_json(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _validate_scores(template, raw_scores):
    if not isinstance(raw_scores, list):
        return None, '评分数据必须是列表。'

    item_ids = set(template.items.values_list('id', flat=True))
    criterion_ids = set(template.criteria.values_list('id', flat=True))
    expected_pairs = {(item_id, criterion_id) for item_id in item_ids for criterion_id in criterion_ids}
    if not expected_pairs:
        return None, '所选模板没有完整的评分对象或标准。'

    normalized = []
    received_pairs = set()
    for entry in raw_scores:
        if not isinstance(entry, dict):
            return None, '评分条目格式无效。'
        try:
            item_id = int(entry.get('itemId'))
            criterion_id = int(entry.get('criterionId'))
            score = int(entry.get('score'))
        except (TypeError, ValueError):
            return None, '评分条目必须包含有效的对象、标准和分数。'
        pair = (item_id, criterion_id)
        if pair not in expected_pairs or pair in received_pairs or not 1 <= score <= 5:
            return None, '评分内容不完整或包含无效数据。'
        received_pairs.add(pair)
        normalized.append((item_id, criterion_id, score))

    if received_pairs != expected_pairs:
        return None, '必须完成所有对象的全部评分。'
    return normalized, None


def _template_data(request, template):
    return {
        'id': template.id,
        'title': template.title,
        'description': template.description,
        'criteria': [
            {'id': criterion.id, 'name': criterion.name, 'weight': criterion.weight}
            for criterion in template.criteria.all()
        ],
        'items': [
            {
                'id': item.id,
                'name': item.name,
                'imageUrl': request.build_absolute_uri(item.image.url) if item.image else '',
            }
            for item in template.items.all()
        ],
    }


def _result_data(request, result):
    template = result.template
    scores = list(result.scores.all())
    score_map = {(score.item_id, score.criterion_id): score.score for score in scores}
    total_weight = sum(criterion.weight for criterion in template.criteria.all())
    ranking = []
    for item in template.items.all():
        weighted_score = sum(
            score_map.get((item.id, criterion.id), 0) * criterion.weight
            for criterion in template.criteria.all()
        )
        ranking.append({
            'itemId': item.id,
            'name': item.name,
            'imageUrl': request.build_absolute_uri(item.image.url) if item.image else '',
            'score': weighted_score / total_weight * 20 if total_weight else 0,
        })
    ranking.sort(key=lambda entry: entry['score'], reverse=True)

    return {
        'id': result.id,
        'resultType': 'human',
        'isPublic': result.is_public,
        'templateHidden': template.is_hidden,
        'createdAt': result.created_at.isoformat(),
        'template': _template_data(request, template),
        'scores': [
            {
                'itemId': score.item_id,
                'criterionId': score.criterion_id,
                'score': score.score,
            }
            for score in scores
        ],
        'ranking': ranking,
    }


def _ai_result_data(request, template):
    ai_take = template.ai_takes
    scores = ai_take.get('scores', [])
    score_map = {
        (entry['itemId'], entry['criterionId']): entry['score']
        for entry in scores
    }
    criteria = list(template.criteria.all())
    total_weight = sum(criterion.weight for criterion in criteria)
    ranking = []
    for item in template.items.all():
        weighted_score = sum(
            score_map.get((item.id, criterion.id), 0) * criterion.weight
            for criterion in criteria
        )
        ranking.append({
            'itemId': item.id,
            'name': item.name,
            'imageUrl': request.build_absolute_uri(item.image.url) if item.image else '',
            'score': weighted_score / total_weight * 20 if total_weight else 0,
        })
    ranking.sort(key=lambda entry: entry['score'], reverse=True)
    return {
        'id': f'ai-{template.id}',
        'resultType': 'ai',
        'aiModel': ai_take.get('model', 'AI'),
        'isPublic': bool(ai_take.get('isPublic', False)),
        'templateHidden': template.is_hidden,
        'createdAt': ai_take['generatedAt'],
        'template': _template_data(request, template),
        'scores': scores,
        'ranking': ranking,
    }


@require_http_methods(['GET', 'POST'])
def rating_collection_view(request):
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)

    if request.method == 'GET':
        results = RatingResult.objects.filter(owner=owner).select_related('template').prefetch_related(
            'template__criteria',
            'template__items',
            'scores',
        ).order_by('-created_at')
        ai_templates = Template.objects.filter(
            owner=owner,
            ai_takes__isnull=False,
        ).prefetch_related('criteria', 'items')
        combined = [
            *[_result_data(request, result) for result in results],
            *[_ai_result_data(request, template) for template in ai_templates],
        ]
        combined.sort(key=lambda entry: entry['createdAt'], reverse=True)
        return JsonResponse({'results': combined})

    data = _read_json(request)
    if data is None:
        return JsonResponse({'detail': '请求内容必须是有效的 JSON 对象。'}, status=400)

    template = get_object_or_404(Template, pk=data.get('templateId'), is_hidden=False)
    normalized_scores, validation_error = _validate_scores(template, data.get('scores'))
    if validation_error:
        return JsonResponse({'detail': validation_error}, status=400)
    is_public = data.get('isPublic', False)
    if not isinstance(is_public, bool):
        return JsonResponse({'detail': '公开状态必须是布尔值。'}, status=400)

    with transaction.atomic():
        # Recheck under the same lock used by moderation before saving a rating.
        template = get_object_or_404(
            Template.objects.select_for_update(), pk=template.pk, is_hidden=False,
        )
        result = RatingResult.objects.create(owner=owner, template=template, is_public=is_public)
        RatingScore.objects.bulk_create([
            RatingScore(result=result, item_id=item_id, criterion_id=criterion_id, score=score)
            for item_id, criterion_id, score in normalized_scores
        ])

    return JsonResponse(_result_data(request, result), status=201)


@require_http_methods(['PATCH', 'DELETE'])
def rating_detail_view(request, result_id):
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)
    result = get_object_or_404(
        RatingResult.objects.select_related('template'),
        pk=result_id,
        owner=owner,
    )

    if request.method == 'DELETE':
        with transaction.atomic():
            result = get_object_or_404(
                RatingResult.objects.select_for_update(), pk=result_id, owner=owner,
            )
            remove_interaction_notifications('rating', result.pk)
            result.delete()
        return JsonResponse({'message': '评分记录已删除。'})

    if result.template.is_hidden:
        return JsonResponse({'detail': 'Template not found.'}, status=404)

    data = _read_json(request)
    if data is None:
        return JsonResponse({'detail': '请求内容必须是有效的 JSON 对象。'}, status=400)

    update_fields = []
    desired_public = None
    if 'isPublic' in data:
        if not isinstance(data['isPublic'], bool):
            return JsonResponse({'detail': '公开状态必须是布尔值。'}, status=400)
        desired_public = data['isPublic']
        update_fields.append('is_public')

    normalized_scores = None
    if 'scores' in data:
        if data.get('templateId') not in (None, result.template_id):
            return JsonResponse({'detail': '不能更改评分记录所属的模板。'}, status=400)
        normalized_scores, validation_error = _validate_scores(result.template, data['scores'])
        if validation_error:
            return JsonResponse({'detail': validation_error}, status=400)

    with transaction.atomic():
        get_object_or_404(
            Template.objects.select_for_update(), pk=result.template_id, is_hidden=False,
        )
        result = get_object_or_404(
            RatingResult.objects.select_for_update(), pk=result_id, owner=owner,
        )
        if update_fields:
            result.is_public = desired_public
            result.save(update_fields=update_fields)
            if not result.is_public:
                remove_interaction_notifications('rating', result.pk)
        if normalized_scores is not None:
            result.scores.all().delete()
            RatingScore.objects.bulk_create([
                RatingScore(result=result, item_id=item_id, criterion_id=criterion_id, score=score)
                for item_id, criterion_id, score in normalized_scores
            ])

    return JsonResponse(_result_data(request, result))
