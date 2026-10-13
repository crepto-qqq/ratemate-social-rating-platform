from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST

from accounts.profiles import current_profile

from .models import Notification


def _recipient(request):
    return current_profile(request)


def _target_url(notification):
    if notification.kind == Notification.MODERATION and notification.action != 'restored':
        return ''
    if notification.target_type == 'template':
        from create_template.models import Template
        template = Template.objects.filter(pk=notification.target_id).first()
        if template is None or getattr(template, 'is_hidden', False):
            return ''
        url = f'/templates/{template.pk}'
    elif notification.target_type == 'rating':
        from rating.public_views import public_results
        if not public_results().filter(pk=notification.target_id).exists():
            return ''
        url = f'/ratings/{notification.target_id}'
    else:
        return ''
    if notification.kind in (Notification.TEMPLATE_COMMENT, Notification.RATING_COMMENT):
        url += '#comments'
    return url


def _data(request, notification):
    actor = notification.actor
    return {
        'id': notification.pk,
        'type': notification.kind,
        'action': notification.action,
        'actorName': actor.userName if actor is not None else notification.actor_name,
        'actorAvatarUrl': request.build_absolute_uri(actor.avatar.url) if actor and actor.avatar else '',
        'summary': notification.summary,
        'preview': notification.preview,
        'targetType': notification.target_type,
        'targetId': notification.target_id,
        'targetUrl': _target_url(notification),
        'reason': notification.reason,
        'createdAt': notification.created_at.isoformat(),
        'isRead': notification.read_at is not None,
    }


@never_cache
@require_GET
def list_view(request):
    recipient = _recipient(request)
    if recipient is None:
        return JsonResponse({'detail': 'Log in to see notifications.'}, status=401)
    raw_page = request.GET.get('page', '1')
    if not raw_page.isascii() or not raw_page.isdigit() or len(raw_page) > 6 or not 1 <= int(raw_page) <= 100000:
        return JsonResponse({'detail': 'Invalid page.'}, status=400)
    unread = request.GET.get('unread', '0')
    if unread not in ('0', '1'):
        return JsonResponse({'detail': 'Invalid unread filter.'}, status=400)
    start = (int(raw_page) - 1) * 20
    queryset = Notification.objects.filter(recipient=recipient).select_related('actor')
    if unread == '1':
        queryset = queryset.filter(read_at__isnull=True)
    notifications = list(queryset[start:start + 21])
    return JsonResponse({
        'notifications': [_data(request, notification) for notification in notifications[:20]],
        'hasMore': len(notifications) > 20,
        'unreadCount': Notification.objects.filter(recipient=recipient, read_at__isnull=True).count(),
    })


@never_cache
@require_GET
def unread_count_view(request):
    recipient = _recipient(request)
    if recipient is None:
        return JsonResponse({'detail': 'Log in to see notifications.'}, status=401)
    return JsonResponse({'unreadCount': Notification.objects.filter(recipient=recipient, read_at__isnull=True).count()})


@require_POST
def mark_read_view(request, notification_id):
    recipient = _recipient(request)
    if recipient is None:
        return JsonResponse({'detail': 'Log in to manage notifications.'}, status=401)
    notification = get_object_or_404(Notification, pk=notification_id, recipient=recipient)
    if notification.read_at is None:
        notification.read_at = timezone.now()
        notification.save(update_fields=['read_at'])
    return JsonResponse({
        'id': notification.pk,
        'isRead': True,
        'unreadCount': Notification.objects.filter(recipient=recipient, read_at__isnull=True).count(),
    })


@require_POST
def mark_all_read_view(request):
    recipient = _recipient(request)
    if recipient is None:
        return JsonResponse({'detail': 'Log in to manage notifications.'}, status=401)
    Notification.objects.filter(recipient=recipient, read_at__isnull=True).update(read_at=timezone.now())
    return JsonResponse({'unreadCount': 0})
