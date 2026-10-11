import json

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods, require_POST

from accounts.profiles import current_profile

from .models import Criterion, Favorite, Item, Template


def _current_owner(request):
    return current_profile(request)


def _read_json_field(request, field_name):
    try:
        value = json.loads(request.POST.get(field_name, '[]'))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, list) else None


def _template_data(request, template, is_favorite=True):
    return {
        'id': template.id,
        'title': template.title,
        'description': template.description,
        'popularity': template.popularity,
        'isFavorite': is_favorite,
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


@require_POST
def create_template_view(request):
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
        try:
            weight = int(criterion.get('weight', 1))
        except (TypeError, ValueError):
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
def favorite_list_view(request):
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)

    favorites = Favorite.objects.filter(user=owner).select_related('template').prefetch_related(
        'template__criteria',
        'template__items',
    ).order_by('-created_at')
    return JsonResponse({
        'templates': [
            _template_data(request, favorite.template)
            for favorite in favorites
        ],
    })


@require_http_methods(['POST', 'DELETE'])
def favorite_detail_view(request, template_id):
    owner = _current_owner(request)
    if owner is None:
        return JsonResponse({'detail': '未找到当前用户。'}, status=404)
    template = get_object_or_404(Template, pk=template_id)

    if request.method == 'POST':
        _, created = Favorite.objects.get_or_create(user=owner, template=template)
        return JsonResponse(
            {
                'isFavorite': True,
                'popularity': template.popularity,
            },
            status=201 if created else 200,
        )

    Favorite.objects.filter(user=owner, template=template).delete()
    return JsonResponse({
        'isFavorite': False,
        'popularity': template.popularity,
    })
