from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_http_methods

from accounts.profiles import current_profile
from create_template.comment_views import _comment_data, _read_content
from create_template.models import Template
from notifications.models import Notification
from notifications.services import (
    notify_interaction, remove_comment_notification, remove_interaction_notification,
    update_comment_notification,
)
from .models import RatingResult, RatingResultLike, RatingResultComment
from .views import _ai_result_data, _result_data


def public_results():
    return RatingResult.objects.filter(is_public=True, template__is_hidden=False).annotate(
        item_count=Count('template__items', distinct=True),
        criterion_count=Count('template__criteria', distinct=True),
        score_count=Count('scores', distinct=True),
    ).filter(item_count__gt=0, criterion_count__gt=0,
             score_count=F('item_count') * F('criterion_count'))


def result_data(request, result):
    data = _result_data(request, result)
    likes = list(result.likes.all())
    data.update({
        'author': {
            'id': result.owner_id, 'name': result.owner.userName,
            'avatarUrl': request.build_absolute_uri(result.owner.avatar.url) if result.owner.avatar else '',
        },
        'likeCount': len(likes),
        'isLiked': request.user.is_authenticated and any(like.user.user_id == request.user.pk for like in likes),
        'isOwner': request.user.is_authenticated and result.owner.user_id == request.user.pk,
        'commentCount': result.comments.count(),
    })
    return data


def ai_result_data(request, template):
    data = _ai_result_data(request, template)
    data.update({
        'author': {
            'id': template.owner_id,
            'name': template.owner.userName,
            'avatarUrl': request.build_absolute_uri(template.owner.avatar.url) if template.owner.avatar else '',
        },
        'likeCount': 0,
        'isLiked': False,
        'isOwner': request.user.is_authenticated and template.owner.user_id == request.user.pk,
        'commentCount': 0,
    })
    return data


def public_ai_templates():
    return Template.objects.filter(
        is_hidden=False,
        ai_takes__isnull=False,
        ai_takes__isPublic=True,
    ).select_related('owner').prefetch_related('criteria', 'items')


def _ai_created_at(template):
    value = template.ai_takes.get('generatedAt')
    return parse_datetime(value) if isinstance(value, str) else None


def public_queryset():
    return public_results().select_related('owner', 'template').prefetch_related(
        'template__criteria', 'template__items', 'scores', 'likes__user', 'comments',
    )


def _locked_public_result(result_id):
    """Recheck visibility while holding the locks used by moderation and privacy updates."""
    candidate = get_object_or_404(RatingResult.objects.only('template_id'), pk=result_id)
    get_object_or_404(
        Template.objects.select_for_update(), pk=candidate.template_id, is_hidden=False,
    )
    result = get_object_or_404(
        RatingResult.objects.select_for_update(), pk=result_id, is_public=True,
    )
    get_object_or_404(public_results(), pk=result_id)
    return result


@require_http_methods(['GET'])
def public_collection_view(request):
    raw_page = request.GET.get('page', '1')
    if not raw_page.isascii() or not raw_page.isdigit() or len(raw_page) > 6 or int(raw_page) < 1:
        return JsonResponse({'detail': 'Invalid page.'}, status=400)
    start = (int(raw_page) - 1) * 20
    queryset = public_queryset()
    ai_queryset = public_ai_templates()
    query = request.GET.get('q', '').strip()[:200]
    if query:
        queryset = queryset.filter(Q(template__title__icontains=query) |
                                   Q(template__description__icontains=query) |
                                   Q(owner__userName__icontains=query))
        ai_queryset = ai_queryset.filter(Q(title__icontains=query) |
                                         Q(description__icontains=query) |
                                         Q(owner__userName__icontains=query))
    limit = start + 21
    combined = [
        *((result.created_at, 'human', result) for result in queryset.order_by('-created_at', '-id')[:limit]),
        *((_ai_created_at(template) or template.updated_at, 'ai', template) for template in ai_queryset),
    ]
    combined.sort(key=lambda entry: (entry[0], entry[2].pk), reverse=True)
    selected = combined[start:start + 21]
    data = [
        ai_result_data(request, value) if kind == 'ai' else result_data(request, value)
        for _, kind, value in selected[:20]
    ]
    return JsonResponse({'results': data, 'hasMore': len(selected) > 20})


@require_http_methods(['GET'])
def public_detail_view(request, result_id):
    return JsonResponse(result_data(request, get_object_or_404(public_queryset(), pk=result_id)))


@require_http_methods(['GET'])
def public_ai_detail_view(request, template_id):
    return JsonResponse(ai_result_data(
        request,
        get_object_or_404(public_ai_templates(), pk=template_id),
    ))


@require_http_methods(['POST', 'DELETE'])
def like_view(request, result_id):
    user = current_profile(request)
    if user is None:
        return JsonResponse({'detail': 'Log in to like a rating.'}, status=401)
    with transaction.atomic():
        if request.method == 'POST':
            result = _locked_public_result(result_id)
        else:
            result = get_object_or_404(RatingResult.objects.select_for_update(), pk=result_id, is_public=True)
            if not public_results().filter(pk=result_id).exists():
                return JsonResponse({'detail': 'Rating not found.'}, status=404)
        if result.owner_id == user.pk:
            return JsonResponse({'detail': 'You cannot like your own rating.'}, status=403)
        if request.method == 'POST':
            like, created = RatingResultLike.objects.get_or_create(result=result, user=user)
            if created:
                notify_interaction(
                    result.owner, user, Notification.RATING_LIKE, like.pk,
                    'rating', result.pk, result.template.title,
                )
        else:
            like = RatingResultLike.objects.filter(result=result, user=user).first()
            if like is not None:
                remove_interaction_notification(Notification.RATING_LIKE, like.pk)
                like.delete()
        return JsonResponse({'isLiked': request.method == 'POST', 'likeCount': result.likes.count()})


@require_http_methods(['GET', 'POST'])
def comment_collection_view(request, result_id):
    if request.method == 'GET':
        result = get_object_or_404(public_results(), pk=result_id)
        raw_page = request.GET.get('page', '1')
        if not raw_page.isascii() or not raw_page.isdigit() or len(raw_page) > 6 or int(raw_page) < 1:
            return JsonResponse({'detail': 'Invalid page.'}, status=400)
        start = (int(raw_page) - 1) * 20
        comments = list(result.comments.select_related('author')[start:start + 21])
        return JsonResponse({'comments': [_comment_data(request, comment) for comment in comments[:20]],
                             'hasMore': len(comments) > 20})
    author = current_profile(request)
    if author is None:
        return JsonResponse({'detail': 'Log in to post a comment.'}, status=401)
    content = _read_content(request)
    if content is None:
        return JsonResponse({'detail': 'Enter a comment between 1 and 2000 characters.'}, status=400)
    with transaction.atomic():
        result = _locked_public_result(result_id)
        comment = RatingResultComment.objects.create(result=result, author=author, content=content)
        notify_interaction(
            result.owner, author, Notification.RATING_COMMENT, comment.pk,
            'rating', result.pk, result.template.title, content,
        )
    return JsonResponse(_comment_data(request, comment), status=201)


@require_http_methods(['PATCH', 'DELETE'])
def comment_detail_view(request, result_id, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Log in to manage comments.'}, status=401)
    comment = get_object_or_404(RatingResultComment.objects.select_related('author'), pk=comment_id, result_id=result_id)
    if request.method != 'DELETE' and not public_results().filter(pk=result_id).exists():
        return JsonResponse({'detail': 'Rating not found.'}, status=404)
    if comment.author.user_id != request.user.pk:
        return JsonResponse({'detail': 'You can only manage your own comments.'}, status=403)
    if request.method == 'DELETE':
        with transaction.atomic():
            remove_comment_notification(Notification.RATING_COMMENT, comment.pk)
            comment.delete()
        return HttpResponse(status=204)
    content = _read_content(request)
    if content is None:
        return JsonResponse({'detail': 'Enter a comment between 1 and 2000 characters.'}, status=400)
    if content != comment.content:
        comment.content = content
        comment.updated_at = timezone.now()
        comment.save(update_fields=['content', 'updated_at'])
        update_comment_notification(Notification.RATING_COMMENT, comment.pk, content)
    return JsonResponse(_comment_data(request, comment))
