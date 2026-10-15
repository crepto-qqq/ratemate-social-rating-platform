from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from accounts.profiles import current_profile
from create_template.models import Template, Favorite
from create_template.views import _template_data
from rating.public_views import public_queryset, result_data
from .service import recommend

@require_http_methods(['GET'])
def recommendation_view(request):
    kind = request.GET.get('kind', 'ratings')
    if kind not in ('ratings', 'templates'):
        return JsonResponse({'detail': 'Invalid recommendation type.'}, status=400)
    raw_page = request.GET.get('page', '1')
    if not raw_page.isascii() or not raw_page.isdigit() or len(raw_page) > 6 or int(raw_page) < 1:
        return JsonResponse({'detail': 'Invalid page.'}, status=400)
    user = current_profile(request)
    ids, reasons, personalized = recommend(request, kind, user)
    start = (int(raw_page) - 1) * 20
    selected = ids[start:start + 20]
    if kind == 'ratings':
        # Recheck visibility even when ranked IDs came from a session cache.
        objects = {result.pk: result for result in public_queryset().filter(pk__in=selected)}
        data = [dict(result_data(request, objects[pk]), recommendationReason=reasons[str(pk)]) for pk in selected if pk in objects]
        field = 'results'
    else:
        favorite_ids = set(Favorite.objects.filter(user=user).values_list('template_id', flat=True)) if user else set()
        objects = {template.pk: template for template in Template.objects.filter(pk__in=selected, is_hidden=False).select_related('owner').prefetch_related('criteria', 'items', 'favorite_records')}
        data = [dict(_template_data(request, objects[pk], pk in favorite_ids), recommendationReason=reasons[str(pk)]) for pk in selected if pk in objects]
        field = 'templates'
    return JsonResponse({field: data, 'hasMore': len(ids) > start + 20, 'personalized': personalized})
