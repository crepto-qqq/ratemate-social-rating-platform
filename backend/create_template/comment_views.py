import json

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.profiles import current_profile
from .models import Comment, Template


def _comment_data(request, comment):
    return {
        'id': comment.id,
        'content': comment.content,
        'createdAt': comment.created_at.isoformat(),
        'updatedAt': (comment.updated_at or comment.created_at).isoformat(),
        'isEdited': comment.updated_at is not None,
        'canManage': request.user.is_authenticated and comment.author.user_id == request.user.pk,
        'author': {
            'id': comment.author_id,
            'name': comment.author.userName,
            'avatarUrl': request.build_absolute_uri(comment.author.avatar.url) if comment.author.avatar else '',
        },
    }


def _read_content(request):
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return None
    content = data.get('content') if isinstance(data, dict) else None
    if not isinstance(content, str):
        return None
    content = content.strip()
    return content if 1 <= len(content) <= 2000 else None


@require_http_methods(['GET', 'POST'])
def comment_collection_view(request, template_id):
    template = get_object_or_404(Template, pk=template_id)
    if request.method == 'GET':
        raw_page = request.GET.get('page', '1')
        if not raw_page.isascii() or not raw_page.isdigit() or len(raw_page) > 7:
            return JsonResponse({'detail': 'Invalid comment page.'}, status=400)
        page = int(raw_page)
        if not 1 <= page <= 1000000:
            return JsonResponse({'detail': 'Invalid comment page.'}, status=400)
        start = (page - 1) * 20
        comments = list(Comment.objects.filter(template=template).select_related('author')[start:start + 21])
        return JsonResponse({
            'comments': [_comment_data(request, comment) for comment in comments[:20]],
            'hasMore': len(comments) > 20,
        })

    author = current_profile(request)
    if author is None:
        return JsonResponse({'detail': 'Log in to post a comment.'}, status=401)
    content = _read_content(request)
    if content is None:
        return JsonResponse({'detail': 'Enter a comment between 1 and 2000 characters.'}, status=400)
    comment = Comment.objects.create(template=template, author=author, content=content)
    return JsonResponse(_comment_data(request, comment), status=201)


@require_http_methods(['PATCH', 'DELETE'])
def comment_detail_view(request, template_id, comment_id):
    if not request.user.is_authenticated:
        return JsonResponse({'detail': 'Log in to manage comments.'}, status=401)
    comment = get_object_or_404(Comment.objects.select_related('author'), pk=comment_id, template_id=template_id)
    if comment.author.user_id != request.user.pk:
        return JsonResponse({'detail': 'You can only manage your own comments.'}, status=403)
    if request.method == 'DELETE':
        comment.delete()
        return HttpResponse(status=204)
    content = _read_content(request)
    if content is None:
        return JsonResponse({'detail': 'Enter a comment between 1 and 2000 characters.'}, status=400)
    if content != comment.content:
        comment.content = content
        comment.updated_at = timezone.now()
        comment.save(update_fields=['content', 'updated_at'])
    return JsonResponse(_comment_data(request, comment))
