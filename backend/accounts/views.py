import json

from django.contrib.auth import authenticate, get_user_model, login
from django.http import JsonResponse
from django.db import transaction
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from .profiles import current_profile, ensure_profile


@never_cache
@require_http_methods(['GET'])
def csrf_view(request):
    return JsonResponse({'csrfToken': get_token(request)})


def _read_credentials(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, None, JsonResponse(
            {'detail': '请求内容必须是有效的 JSON。'},
            status=400,
        )

    if not isinstance(data, dict):
        return None, None, JsonResponse(
            {'detail': '请求内容必须是 JSON 对象。'},
            status=400,
        )

    username = data.get('username')
    password = data.get('password')

    if not isinstance(username, str) or not isinstance(password, str):
        return None, None, JsonResponse(
            {'detail': '用户名和密码不能为空。'},
            status=400,
        )

    username = username.strip()
    if not username or not password:
        return None, None, JsonResponse(
            {'detail': '用户名和密码不能为空。'},
            status=400,
        )

    return username, password, None


@require_POST
def register_view(request):
    username, password, error_response = _read_credentials(request)
    if error_response:
        return error_response

    if len(username) < 3 or len(username) > 30:
        return JsonResponse(
            {'detail': '用户名长度必须为 3 到 30 个字符。'},
            status=400,
        )
    if len(password) < 6:
        return JsonResponse(
            {'detail': '密码不能少于 6 个字符。'},
            status=400,
        )

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return JsonResponse({'detail': '该用户名已被使用。'}, status=409)

    with transaction.atomic():
        user = User.objects.create_user(username=username, password=password)
        ensure_profile(user)
    return JsonResponse({'message': '注册成功，请登录。'}, status=201)


@require_POST
def login_view(request):
    username, password, error_response = _read_credentials(request)
    if error_response:
        return error_response

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({'detail': '用户名或密码错误。'}, status=401)

    login(request, user)
    return JsonResponse({'message': '登录成功！'})


def _profile_response(request, profile):
    avatar_url = ''
    if profile.avatar:
        avatar_url = request.build_absolute_uri(profile.avatar.url)

    return {
        'id': profile.id,
        'userName': profile.userName,
        'email': '' if profile.email.endswith('@profiles.invalid') else profile.email,
        'avatarUrl': avatar_url,
        'bio': profile.bio,
    }


def _current_profile(request):
    return current_profile(request)


@require_http_methods(['GET', 'POST'])
def profile_view(request):
    profile = _current_profile(request)
    if profile is None:
        return JsonResponse({'detail': '未找到当前用户的个人资料。'}, status=404)

    if request.method == 'GET':
        return JsonResponse(_profile_response(request, profile))

    username = request.POST.get('userName', profile.userName).strip()
    bio = request.POST.get('bio', profile.bio)
    password = request.POST.get('password', '')
    avatar = request.FILES.get('avatar')

    if not 3 <= len(username) <= 30:
        return JsonResponse({'detail': '用户名长度必须为 3 到 30 个字符。'}, status=400)
    if len(bio) > 300:
        return JsonResponse({'detail': '简介不能超过 300 个字符。'}, status=400)
    if password and len(password) < 6:
        return JsonResponse({'detail': '新密码不能少于 6 个字符。'}, status=400)
    if avatar and avatar.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        return JsonResponse({'detail': '头像必须是 JPG、PNG 或 WebP 图片。'}, status=400)
    if avatar and avatar.size > 5 * 1024 * 1024:
        return JsonResponse({'detail': '头像不能超过 5 MB。'}, status=400)

    profile.userName = username
    profile.bio = bio
    if password:
        profile.set_password(password)
    if avatar:
        profile.avatar = avatar
    profile.save()

    response = _profile_response(request, profile)
    response['message'] = '个人资料已更新。'
    return JsonResponse(response)
