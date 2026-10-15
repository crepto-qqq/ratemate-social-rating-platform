from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.profiles import current_profile
from moderation.models import ModerationAction
from rating.models import RatingResult

from .models import Template


@require_GET
def hidden_content_view(request):
    """Let affected authors see a hidden template's status without exposing its body."""
    owner = current_profile(request)
    if owner is None:
        return JsonResponse({'detail': 'Log in to see your content.'}, status=401)

    templates = list(
        Template.objects.filter(owner=owner, is_hidden=True)
        .annotate(rating_count=Count('rating_results', distinct=True))
        .order_by('-updated_at', '-id')
    )
    ratings = list(
        RatingResult.objects.filter(owner=owner, template__is_hidden=True)
        .select_related('template')
        .order_by('-created_at', '-id')
    )
    template_ids = {template.pk for template in templates}
    template_ids.update(rating.template_id for rating in ratings)
    latest_hide = {}
    for action in ModerationAction.objects.filter(
        action=ModerationAction.HIDE_TEMPLATE,
        target_type='template',
        target_id__in=template_ids,
    ).order_by('-created_at', '-id'):
        latest_hide.setdefault(action.target_id, action)

    def status(template_id):
        action = latest_hide.get(template_id)
        return {
            'reason': action.reason if action else '',
            'hiddenAt': action.created_at.isoformat() if action else None,
        }

    return JsonResponse({
        'templates': [
            {
                'id': template.pk,
                'title': template.title,
                'ratingCount': template.rating_count,
                **status(template.pk),
            }
            for template in templates
        ],
        'ratings': [
            {
                'id': rating.pk,
                'templateId': rating.template_id,
                'templateTitle': rating.template.title,
                **status(rating.template_id),
            }
            for rating in ratings
        ],
    })
