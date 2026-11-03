import json

from django.conf import settings
from django.core.exceptions import ValidationError
from config.uploads import sanitize_image
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.profiles import current_profile
from notifications.models import Notification
from notifications.services import notify_interaction, remove_interaction_notification

from .ai_takes import AIRatingError, generate_ai_take_scores
from .models import Criterion, Favorite, Item, Template


def _current_owner(request):
    if not hasattr(request, '_ratemate_profile'):
        request._ratemate_profile = current_profile(request)
    return request._ratemate_profile


def _read_json_field(request, field_name):
    try:
        value = json.loads(request.POST.get(field_name, '[]'))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, list) else None


def _template_data(request, template, is_favorite=True):
    viewer = _current_owner(request)
    return {
        'id': template.id,
        'title': template.title,
        'description': template.description,
        'popularity': template.popularity,
        'isFavorite': is_favorite,
        'isOwner': viewer is not None and viewer.pk == template.owner_id,
        'hasAiTake': template.ai_takes is not None,
        'author': {
            'id': template.owner_id,
            'name': template.owner.userName,
            'avatarUrl': request.build_absolute_uri(template.owner.avatar.url) if template.owner.avatar else '',
        },
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


@require_http_methods(['GET', 'POST'])
def create_template_view(request):
    if request.method == 'GET':
        viewer = _current_owner(request)
        templates = Template.objects.filter(is_hidden=False).select_related('owner').prefetch_related(
            'criteria', 'items', 'favorite_records',
        ).order_by('-created_at', '-id')
        raw_page = request.GET.get('page')
        if raw_page is not None:
            if not raw_page.isascii() or not raw_page.isdigit() or len(raw_page) > 6 or int(raw_page) < 1:
                return JsonResponse({'detail': 'Invalid page.'}, status=400)
            query = request.GET.get('q', '').strip()[:200]
            if query:
                templates = templates.filter(Q(title__icontains=query) |
                                             Q(description__icontains=query) |
                                             Q(owner__userName__icontains=query))
            start = (int(raw_page) - 1) * 10
            selected = list(templates[start:start + 11])
            templates = selected[:10]
        favorite_ids = set(Favorite.objects.filter(user=viewer).values_list('template_id', flat=True)) if viewer else set()
        data = {'templates': [
            _template_data(request, template, template.id in favorite_ids)
            for template in templates
        ]}
        if raw_page is not None:
            data['hasMore'] = len(selected) > 10
        return JsonResponse(data)
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    criteria = _read_json_field(request, 'criteria')
    items = _read_json_field(request, 'items')

    if not title or len(title) > 120:
        return JsonResponse({'detail': '模板名称不能为空且不能超过 120 个字符。'}, status=400)
    if criteria is None or not criteria:
        return JsonResponse({'detail': '至少需要一个评分标准。'}, status=400)
    if items is None or not items:
        return JsonResponse({'detail': '至少需要一个待评分对象。'}, status=400)

    normalized_criteria = []
    for index, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            return JsonResponse({'detail': '评分标准格式无效。'}, status=400)
        name = str(criterion.get('name', '')).strip()
        weight = criterion.get('weight', 1)
        if type(weight) is not int:
            return JsonResponse({'detail': '评分标准权重必须是整数。'}, status=400)
        if not name or len(name) > 100 or not 1 <= weight <= 10:
            return JsonResponse({'detail': '评分标准名称或权重无效。'}, status=400)
        normalized_criteria.append({'name': name, 'weight': weight, 'order': index})

    normalized_items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            return JsonResponse({'detail': '待评分对象格式无效。'}, status=400)
        name = str(item.get('name', '')).strip()
        if not name or len(name) > 120:
            return JsonResponse({'detail': '待评分对象名称无效。'}, status=400)
        image = request.FILES.get(f'item_image_{index}')
        if image is None:
            return JsonResponse({'detail': '每个待评分对象都需要图片。'}, status=400)
        if image and image.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
            return JsonResponse({'detail': '对象图片必须是 JPG、PNG 或 WebP。'}, status=400)
        if image and image.size > 5 * 1024 * 1024:
            return JsonResponse({'detail': '对象图片不能超过 5 MB。'}, status=400)
        try:
            image = sanitize_image(image)
        except ValidationError as exc:
            return JsonResponse({'detail': exc.messages[0]}, status=400)
        normalized_items.append({'name': name, 'image': image, 'order': index})

    with transaction.atomic():
        template = Template.objects.create(
            owner=owner,
            title=title,
            description=description,
        )
        for criterion in normalized_criteria:
            Criterion.objects.create(template=template, **criterion)
        for item in normalized_items:
            Item.objects.create(template=template, **item)
        template.criteria_locked = True
        template.save(update_fields=['criteria_locked', 'updated_at'])
        Favorite.objects.create(user=owner, template=template)

    return JsonResponse(
        {
            'id': template.id,
            'title': template.title,
            'popularity': template.popularity,
            'message': '模板创建成功。',
        },
        status=201,
    )


@require_http_methods(['GET'])
def template_detail_view(request, template_id):
    template = get_object_or_404(
        Template.objects.filter(is_hidden=False).select_related('owner').prefetch_related('criteria', 'items', 'favorite_records'),
        pk=template_id,
    )
    viewer = _current_owner(request)
    is_favorite = Favorite.objects.filter(user=viewer, template=template).exists() if viewer else False
    return JsonResponse(_template_data(request, template, is_favorite))


@require_http_methods(['GET'])
def favorite_list_view(request):
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)

    favorites = Favorite.objects.filter(user=owner, template__is_hidden=False).select_related('template').prefetch_related(
        'template__criteria',
        'template__items',
    ).order_by('-created_at', '-id')
    raw_page = request.GET.get('page')
    if raw_page is not None:
        if not raw_page.isascii() or not raw_page.isdigit() or len(raw_page) > 6 or int(raw_page) < 1:
            return JsonResponse({'detail': 'Invalid page.'}, status=400)
        start = (int(raw_page) - 1) * 10
        selected = list(favorites[start:start + 11])
        favorites = selected[:10]
    data = {
        'templates': [
            _template_data(request, favorite.template)
            for favorite in favorites
        ],
    }
    if raw_page is not None:
        data['hasMore'] = len(selected) > 10
    return JsonResponse(data)


@require_http_methods(['POST', 'PATCH', 'DELETE'])
def ai_take_view(request, template_id):
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)

    template = get_object_or_404(
        Template.objects.select_related('owner').prefetch_related('criteria', 'items'),
        pk=template_id,
        owner=owner,
    )
    if request.method == 'DELETE':
        if template.ai_takes is None:
            return JsonResponse({'detail': '该模板没有 AI 评分。'}, status=404)
        Template.objects.filter(pk=template.pk, owner=owner).update(
            ai_takes=None,
            updated_at=timezone.now(),
        )
        return JsonResponse({'message': 'AI 评分已删除。'})

    if template.is_hidden:
        return JsonResponse({'detail': 'Template not found.'}, status=404)

    if request.method == 'PATCH':
        if template.ai_takes is None:
            return JsonResponse({'detail': '该模板没有 AI 评分。'}, status=404)
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'detail': '请求内容必须是有效的 JSON 对象。'}, status=400)
        is_public = data.get('isPublic') if isinstance(data, dict) else None
        if type(is_public) is not bool:
            return JsonResponse({'detail': '公开状态必须是布尔值。'}, status=400)
        ai_take = {**template.ai_takes, 'isPublic': is_public}
        Template.objects.filter(pk=template.pk, owner=owner).update(
            ai_takes=ai_take,
            updated_at=timezone.now(),
        )
        return JsonResponse({'aiTake': ai_take})

    if template.ai_takes is not None:
        return JsonResponse({'detail': '该模板已经有 AI 评分，请先删除后再重新生成。'}, status=409)

    try:
        scores = generate_ai_take_scores(template)
    except AIRatingError as error:
        return JsonResponse({'detail': str(error)}, status=502)

    generated_at = timezone.now()
    ai_take = {
        'generatedAt': generated_at.isoformat(),
        'model': settings.OPENAI_MODEL,
        'isPublic': False,
        'scores': scores,
    }
    updated = Template.objects.filter(
        pk=template.pk,
        owner=owner,
        ai_takes__isnull=True,
    ).update(ai_takes=ai_take, updated_at=generated_at)
    if not updated:
        return JsonResponse({'detail': '该模板已经有 AI 评分，请先删除后再重新生成。'}, status=409)
    return JsonResponse({'aiTake': ai_take}, status=201)


@require_http_methods(['POST', 'DELETE'])
def favorite_detail_view(request, template_id):
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)
    if request.method == 'POST':
        with transaction.atomic():
            template = get_object_or_404(
                Template.objects.select_for_update(), pk=template_id, is_hidden=False,
            )
            favorite, created = Favorite.objects.get_or_create(user=owner, template=template)
            if created:
                notify_interaction(
                    template.owner, owner, Notification.TEMPLATE_FAVORITE, favorite.pk,
                    'template', template.pk, template.title,
                )
        return JsonResponse(
            {
                'isFavorite': True,
                'popularity': template.popularity,
            },
            status=201 if created else 200,
        )

    template = get_object_or_404(Template, pk=template_id)
    with transaction.atomic():
        favorite = Favorite.objects.filter(user=owner, template=template).first()
        if favorite is not None:
            remove_interaction_notification(Notification.TEMPLATE_FAVORITE, favorite.pk)
            favorite.delete()
    return JsonResponse({
        'isFavorite': False,
        'popularity': template.popularity,
    })
