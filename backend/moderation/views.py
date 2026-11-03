import json
from functools import wraps

from django.db import transaction
from django.db.models import Count, F, Q, Value
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from accounts.models import User_profile
from accounts.profiles import current_profile
from create_template.models import Comment, Template
from rating.models import RatingResult, RatingResultComment
from rating.views import _result_data

from .models import ModerationAction


PAGE_SIZE = 20


def staff_required(view):
    @wraps(view)
    def guarded(request, *args, **kwargs):
        if current_profile(request) is None:
            return JsonResponse({'detail': 'Log in to manage content.'}, status=401)
        if not (request.user.is_staff or request.user.is_superuser):
            return JsonResponse({'detail': 'Administrator access required.'}, status=403)
        return view(request, *args, **kwargs)

    return guarded


def _page(request):
    raw = request.GET.get('page', '1')
    if not raw.isascii() or not raw.isdigit() or len(raw) > 7:
        return None
    page = int(raw)
    return page if 1 <= page <= 1000000 else None


def _paginate(request, queryset, key, serializer):
    page = _page(request)
    if page is None:
        return JsonResponse({'detail': 'Invalid page.'}, status=400)
    start = (page - 1) * PAGE_SIZE
    objects = list(queryset[start:start + PAGE_SIZE + 1])
    return JsonResponse({key: [serializer(obj) for obj in objects[:PAGE_SIZE]], 'hasMore': len(objects) > PAGE_SIZE})


def _profile_data(profile):
    return {'id': profile.pk, 'name': profile.userName, 'email': profile.email}


def _action_data(action):
    return {
        'id': action.pk,
        'action': action.action,
        'targetType': action.target_type,
        'targetId': action.target_id,
        'targetLabel': action.target_label,
        'reason': action.reason,
        'actor': {'id': action.actor_id, 'name': action.actor_name},
        'createdAt': action.created_at.isoformat(),
    }


def _record(request, action, target_type, target_id, target_label, reason):
    return ModerationAction.objects.create(
        actor=request.user,
        actor_name=request.user.get_username(),
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_label=target_label[:200],
        reason=reason,
    )


def _reason(request):
    try:
        body = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(body, dict) or not isinstance(body.get('reason'), str):
        return None
    reason = body['reason'].strip()
    return reason if 1 <= len(reason) <= 1000 else None


def _success(message, action):
    return JsonResponse({'message': message, 'action': _action_data(action)})


@require_GET
def me_view(request):
    return JsonResponse({'isAdmin': current_profile(request) is not None and (request.user.is_staff or request.user.is_superuser)})


@staff_required
@require_GET
def users_view(request):
    query = request.GET.get('q', '').strip()[:200]
    users = User_profile.objects.select_related('user').order_by('-id')
    if query:
        users = users.filter(Q(userName__icontains=query) | Q(email__icontains=query) | Q(user__username__icontains=query))
    return _paginate(request, users, 'users', lambda profile: {
        **_profile_data(profile),
        'joinedAt': profile.user.date_joined.isoformat() if profile.user_id else None,
        'isStaff': bool(profile.user and (profile.user.is_staff or profile.user.is_superuser)),
    })


@staff_required
@require_GET
def templates_view(request):
    query = request.GET.get('q', '').strip()[:200]
    templates = Template.objects.select_related('owner').annotate(
        rating_count=Count('rating_results', filter=Q(rating_results__is_public=True), distinct=True),
        comment_count=Count('comments', distinct=True),
        favorite_count=Count('favorite_records', distinct=True),
    ).order_by('-created_at', '-id')
    if query:
        templates = templates.filter(Q(title__icontains=query) | Q(description__icontains=query) |
                                     Q(owner__userName__icontains=query))
    return _paginate(request, templates, 'templates', lambda template: {
        'id': template.pk,
        'title': template.title,
        'description': template.description,
        'owner': _profile_data(template.owner),
        'createdAt': template.created_at.isoformat(),
        'isHidden': template.is_hidden,
        'ratingCount': template.rating_count,
        'commentCount': template.comment_count,
        'favoriteCount': template.favorite_count,
    })


@staff_required
@require_GET
def template_detail_view(request, template_id):
    template = get_object_or_404(
        Template.objects.select_related('owner').prefetch_related('criteria', 'items'), pk=template_id,
    )
    return JsonResponse({'template': {
        'id': template.pk,
        'title': template.title,
        'description': template.description,
        'owner': _profile_data(template.owner),
        'createdAt': template.created_at.isoformat(),
        'isHidden': template.is_hidden,
        'ratingCount': template.rating_results.filter(is_public=True).count(),
        'commentCount': template.comments.count(),
        'favoriteCount': template.favorite_records.count(),
        'criteria': [
            {'id': criterion.pk, 'name': criterion.name, 'weight': criterion.weight}
            for criterion in template.criteria.all()
        ],
        'items': [
            {
                'id': item.pk,
                'name': item.name,
                'imageUrl': request.build_absolute_uri(item.image.url) if item.image else '',
            }
            for item in template.items.all()
        ],
    }})


@staff_required
@require_GET
def ratings_view(request):
    query = request.GET.get('q', '').strip()[:200]
    ratings = RatingResult.objects.filter(is_public=True).select_related('owner', 'template').annotate(
        comment_count=Count('comments', distinct=True),
        like_count=Count('likes', distinct=True),
    ).order_by('-created_at', '-id')
    if query:
        ratings = ratings.filter(Q(template__title__icontains=query) |
                                 Q(owner__userName__icontains=query) |
                                 Q(template__description__icontains=query))
    return _paginate(request, ratings, 'ratings', lambda rating: {
        'id': rating.pk,
        'templateId': rating.template_id,
        'templateTitle': rating.template.title,
        'templateHidden': rating.template.is_hidden,
        'owner': _profile_data(rating.owner),
        'createdAt': rating.created_at.isoformat(),
        'commentCount': rating.comment_count,
        'likeCount': rating.like_count,
    })


@staff_required
@require_GET
def rating_detail_view(request, rating_id):
    rating = get_object_or_404(
        RatingResult.objects.filter(is_public=True).select_related('owner', 'template').prefetch_related(
            'template__criteria', 'template__items', 'scores',
        ), pk=rating_id,
    )
    data = _result_data(request, rating)
    data.update({
        'owner': _profile_data(rating.owner),
        'templateHidden': rating.template.is_hidden,
        'commentCount': rating.comments.count(),
        'likeCount': rating.likes.count(),
    })
    return JsonResponse({'rating': data})


def _template_comments(query):
    comments = Comment.objects.order_by()
    if query:
        comments = comments.filter(Q(content__icontains=query) | Q(author__userName__icontains=query) |
                                   Q(template__title__icontains=query))
    return comments.annotate(
        kind=Value('template'), post_id=F('template_id'), post_title=F('template__title'),
        template_hidden=F('template__is_hidden'),
        author_name=F('author__userName'), author_email=F('author__email'),
    ).values('id', 'kind', 'content', 'author_id', 'author_name', 'author_email',
             'post_id', 'post_title', 'template_hidden', 'created_at')


def _rating_comments(query):
    comments = RatingResultComment.objects.filter(result__is_public=True).order_by()
    if query:
        comments = comments.filter(Q(content__icontains=query) | Q(author__userName__icontains=query) |
                                   Q(result__template__title__icontains=query))
    return comments.annotate(
        kind=Value('rating'), post_id=F('result_id'), post_title=F('result__template__title'),
        template_hidden=F('result__template__is_hidden'),
        author_name=F('author__userName'), author_email=F('author__email'),
    ).values('id', 'kind', 'content', 'author_id', 'author_name', 'author_email',
             'post_id', 'post_title', 'template_hidden', 'created_at')


@staff_required
@require_GET
def comments_view(request):
    kind = request.GET.get('kind', '')
    if kind not in ('', 'template', 'rating'):
        return JsonResponse({'detail': 'Invalid comment kind.'}, status=400)
    query = request.GET.get('q', '').strip()[:200]
    if kind == 'template':
        comments = _template_comments(query)
    elif kind == 'rating':
        comments = _rating_comments(query)
    else:
        comments = _template_comments(query).union(_rating_comments(query))
    comments = comments.order_by('-created_at', '-id', 'kind')
    return _paginate(request, comments, 'comments', lambda comment: {
        'id': comment['id'],
        'kind': comment['kind'],
        'content': comment['content'],
        'author': {'id': comment['author_id'], 'name': comment['author_name'], 'email': comment['author_email']},
        'postId': comment['post_id'],
        'postTitle': comment['post_title'],
        'templateHidden': comment['template_hidden'],
        'createdAt': comment['created_at'].isoformat(),
    })


@staff_required
@require_GET
def actions_view(request):
    query = request.GET.get('q', '').strip()[:200]
    actions = ModerationAction.objects.order_by('-created_at', '-id')
    if query:
        actions = actions.filter(Q(target_label__icontains=query) | Q(reason__icontains=query) |
                                 Q(actor_name__icontains=query))
    return _paginate(request, actions, 'actions', _action_data)


@staff_required
@require_POST
def hide_template_view(request, template_id):
    return _change_template_visibility(request, template_id, True)


@staff_required
@require_POST
def restore_template_view(request, template_id):
    return _change_template_visibility(request, template_id, False)


def _change_template_visibility(request, template_id, hidden):
    reason = _reason(request)
    if reason is None:
        return JsonResponse({'detail': 'Enter a reason between 1 and 1000 characters.'}, status=400)

    from notifications.services import notify_moderation, remove_interaction_notifications

    with transaction.atomic():
        template = get_object_or_404(Template.objects.select_related('owner').select_for_update(), pk=template_id)
        if template.is_hidden == hidden:
            return JsonResponse({'detail': 'Template is already in the requested state.'}, status=400)

        template.is_hidden = hidden
        template.save(update_fields=['is_hidden', 'updated_at'])
        action = _record(
            request,
            ModerationAction.HIDE_TEMPLATE if hidden else ModerationAction.RESTORE_TEMPLATE,
            'template', template.pk, template.title, reason,
        )
        if hidden:
            remove_interaction_notifications('template', template.pk)
            for rating_id in RatingResult.objects.filter(template=template, is_public=True).values_list('id', flat=True):
                remove_interaction_notifications('rating', rating_id)

        notify_moderation(template.owner, 'hidden' if hidden else 'restored',
                          'template', template.pk, template.title, reason)
        affected_owners = User_profile.objects.filter(
            rating_results__template=template, rating_results__is_public=True,
        ).exclude(pk=template.owner_id).distinct()
        for owner in affected_owners:
            notify_moderation(owner, 'hidden' if hidden else 'restored',
                              'template', template.pk, template.title, reason)

    return _success('Template hidden.' if hidden else 'Template restored.', action)


@staff_required
@require_POST
def remove_rating_view(request, rating_id):
    reason = _reason(request)
    if reason is None:
        return JsonResponse({'detail': 'Enter a reason between 1 and 1000 characters.'}, status=400)

    from notifications.services import notify_moderation, remove_interaction_notifications

    with transaction.atomic():
        rating = get_object_or_404(
            RatingResult.objects.select_related('owner', 'template').select_for_update(),
            pk=rating_id, is_public=True,
        )
        label = f'{rating.template.title} · 评分 #{rating.pk}'
        action = _record(request, ModerationAction.REMOVE_RATING, 'rating', rating.pk, label, reason)
        remove_interaction_notifications('rating', rating.pk)
        notify_moderation(rating.owner, 'removed', 'rating', rating.pk, label[:200], reason)
        rating.delete()

    return _success('Public rating removed.', action)


@staff_required
@require_POST
def remove_template_comment_view(request, comment_id):
    return _remove_comment(request, 'template', comment_id)


@staff_required
@require_POST
def remove_rating_comment_view(request, comment_id):
    return _remove_comment(request, 'rating', comment_id)


def _remove_comment(request, kind, comment_id):
    reason = _reason(request)
    if reason is None:
        return JsonResponse({'detail': 'Enter a reason between 1 and 1000 characters.'}, status=400)

    from notifications.services import notify_moderation, remove_comment_notification

    with transaction.atomic():
        if kind == 'template':
            comment = get_object_or_404(
                Comment.objects.select_related('author', 'template').select_for_update(), pk=comment_id,
            )
            title = comment.template.title
            action_type = ModerationAction.REMOVE_TEMPLATE_COMMENT
            notice_kind = 'template_comment'
        else:
            comment = get_object_or_404(
                RatingResultComment.objects.select_related('author', 'result__template').select_for_update(),
                pk=comment_id, result__is_public=True,
            )
            title = comment.result.template.title
            action_type = ModerationAction.REMOVE_RATING_COMMENT
            notice_kind = 'rating_comment'

        label = f'{title} · 评论 #{comment.pk}'
        action = _record(request, action_type, 'comment', comment.pk, label, reason)
        remove_comment_notification(notice_kind, comment.pk)
        notify_moderation(comment.author, 'removed', 'comment', comment.pk, label[:200], reason)
        comment.delete()

    return _success('Comment removed.', action)
