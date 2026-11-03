import json
import hashlib
import re
import secrets
from datetime import timedelta
from uuid import UUID, uuid4

from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from .models import AccountSecurity, OtpChallenge, User_profile
from .profiles import current_profile, ensure_profile
from .throttling import reserve_login_attempt
from config.uploads import sanitize_image


@never_cache
@require_http_methods(['GET'])
def csrf_view(request):
    return JsonResponse({'csrfToken': get_token(request)})


def _body(request):
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _error(message, status=400):
    return JsonResponse({'detail': message}, status=status)


def _credentials(request):
    data = _body(request)
    if data is None or not isinstance(data.get('username'), str) or not isinstance(data.get('password'), str):
        return None, None, _error('Username and password are required.')
    username, password = data['username'].strip(), data['password']
    if not username or not password:
        return None, None, _error('Username and password are required.')
    return username, password, None


def _email(value):
    if not isinstance(value, str):
        return None
    value = value.strip().lower()
    from django.core.validators import validate_email
    try:
        validate_email(value)
    except ValidationError:
        return None
    return value if len(value) <= 254 else None


def _email_taken(email, user=None):
    users = get_user_model().objects.filter(email__iexact=email)
    profiles = User_profile.objects.filter(email__iexact=email)
    if user is not None:
        users = users.exclude(pk=user.pk)
        profiles = profiles.exclude(user=user)
    return users.exists() or profiles.exists()


def _session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


def _send_challenge(request, user, purpose):
    now = timezone.now()
    if _too_many_attempts(user):
        return None, _error('Too many incorrect codes. Try again in 10 minutes.', 429)
    if OtpChallenge.objects.filter(user=user, last_sent_at__gte=now - timedelta(hours=1)).count() >= 10:
        return None, _error('Too many codes requested. Try again later.', 429)
    code = f'{secrets.randbelow(1000000):06d}'
    challenge = OtpChallenge(user=user, purpose=purpose, code_hash=make_password(code),
                             session_key=_session_key(request), expires_at=now + timedelta(minutes=5),
                             last_sent_at=now)
    subject = {
        OtpChallenge.ACTIVATION: 'RateMate email verification',
        OtpChallenge.LOGIN: 'RateMate login code',
        OtpChallenge.RESET: 'RateMate password reset code',
    }[purpose]
    try:
        message = (f'Your RateMate password reset code is {code}. It expires in 5 minutes.'
                   if purpose == OtpChallenge.RESET else f'Your RateMate code is {code}. It expires in 5 minutes.')
        send_mail(subject, message, None,
                  [user.email], fail_silently=False)
    except Exception:
        return None, _error('Could not send the email. Please try again later.', 503)
    OtpChallenge.objects.filter(user=user, purpose=purpose, consumed=False).update(consumed=True)
    challenge.save()
    return challenge, None


def _pending_registration_step(pending, status=200):
    local, domain = pending['email'].split('@', 1)
    return JsonResponse({
        'step': OtpChallenge.ACTIVATION,
        'challengeId': pending['challenge_id'],
        'maskedEmail': f'{local[:1]}***@{domain}',
        'retryAfter': 60,
        'detail': 'Check your email for a six-digit code.',
    }, status=status)


def _send_pending_registration(request, username, email, password_hash, *, attempts=0, sent_count=0):
    code = f'{secrets.randbelow(1000000):06d}'
    try:
        send_mail('RateMate email verification',
                  f'Your RateMate code is {code}. It expires in 5 minutes.',
                  None, [email], fail_silently=False)
    except Exception:
        return _error('Could not send the email. Please try again later.', 503)
    now = timezone.now().timestamp()
    pending = {
        'challenge_id': str(uuid4()),
        'username': username,
        'email': email,
        'password_hash': password_hash,
        'code_hash': make_password(code),
        'expires_at': now + 5 * 60,
        'last_sent_at': now,
        'attempts': attempts,
        'sent_count': sent_count + 1,
    }
    request.session['pending_registration'] = pending
    return _pending_registration_step(pending, 202 if sent_count == 0 else 200)


def _verify_pending_registration(request, pending, code):
    if not isinstance(code, str) or not re.fullmatch(r'\d{6}', code):
        return _error('Invalid or expired code.')
    if pending['attempts'] >= 5:
        return _error('Too many incorrect codes. Try again later.', 429)
    if pending['expires_at'] <= timezone.now().timestamp():
        return _error('Invalid or expired code.')
    if not check_password(code, pending['code_hash']):
        pending['attempts'] += 1
        request.session['pending_registration'] = pending
        return _error('Invalid or expired code.')
    User = get_user_model()
    if User.objects.filter(username__iexact=pending['username']).exists() or _email_taken(pending['email']):
        return _error('Username or email is already in use.', 409)
    try:
        with transaction.atomic():
            user = User(username=pending['username'], email=pending['email'],
                        password=pending['password_hash'], is_active=True)
            user.save()
            AccountSecurity.objects.create(user=user, email_verified=True)
            ensure_profile(user)
    except IntegrityError:
        return _error('Username or email is already in use.', 409)
    request.session.pop('pending_registration', None)
    return JsonResponse({'step': 'login_required', 'detail': 'Email verified. Sign in to continue.'})


def _too_many_attempts(user):
    total = OtpChallenge.objects.filter(
        user=user, last_sent_at__gte=timezone.now() - timedelta(minutes=10),
    ).aggregate(total=Sum('attempts'))['total'] or 0
    return total >= 5


def _step(challenge, status=200):
    email = challenge.user.email
    local, domain = email.split('@', 1)
    return JsonResponse({'step': challenge.purpose, 'challengeId': str(challenge.pk),
                         'maskedEmail': f'{local[:1]}***@{domain}', 'retryAfter': 60,
                         'detail': 'Check your email for a six-digit code.'}, status=status)


def _validate_new_password(password, user):
    if not re.search('[A-Z]', password) or not re.search('[a-z]', password) or not re.search('[0-9]', password):
        return 'Password must include uppercase and lowercase letters and a number.'
    try:
        validate_password(password, user)
    except ValidationError as exc:
        return ' '.join(exc.messages)
    return None


@require_POST
def register_view(request):
    username, password, error = _credentials(request)
    if error:
        return error
    email = _email(_body(request).get('email'))
    if not email:
        return _error('A valid email address is required.')
    if not 3 <= len(username) <= 30:
        return _error('Username must be 3 to 30 characters long.')
    User = get_user_model()
    problem = _validate_new_password(password, User(username=username, email=email))
    if problem:
        return _error(problem)
    if User.objects.filter(username__iexact=username).exists():
        return _error('Username is already in use.', 409)
    if _email_taken(email):
        return _error('Email is already in use.', 409)
    return _send_pending_registration(request, username, email, make_password(password))


@require_POST
def login_view(request):
    username, password, error = _credentials(request)
    if error:
        return error
    retry_after = reserve_login_attempt(username)
    if retry_after:
        response = _error('Too many sign-in attempts. Try again later.', 429)
        response['Retry-After'] = str(retry_after)
        return response
    user = get_user_model().objects.filter(username=username).first()
    if user is None:
        make_password(password)
    if user is None or not user.check_password(password):
        return _error('Invalid username or password.', 401)
    security = AccountSecurity.objects.filter(user=user).first()
    if security is None:
        if not user.is_active:
            return _error('This account is disabled.', 403)
        request.session['pending_email_user'] = user.pk
        return JsonResponse({'step': 'email_required', 'detail': 'Add and verify your email address before signing in.'})
    request.session.pop('pending_email_user', None)
    if not security.email_verified:
        purpose = OtpChallenge.ACTIVATION
    elif user.is_active:
        purpose = OtpChallenge.LOGIN
    else:
        return _error('This account is disabled.', 403)
    challenge, error = _send_challenge(request, user, purpose)
    return error or _step(challenge)


@require_POST
def enroll_email_view(request):
    user_id = request.session.get('pending_email_user')
    user = get_user_model().objects.filter(pk=user_id).first() if user_id else None
    if user is None or not user.is_active or AccountSecurity.objects.filter(user=user).exists():
        return _error('Sign in with your username and password first.', 403)
    data = _body(request)
    email = _email(data.get('email')) if data else None
    if not email:
        return _error('A valid email address is required.')
    if _email_taken(email, user):
        return _error('Email is already in use.', 409)
    previous = user.email
    user.email = email
    user.save(update_fields=['email'])
    challenge, error = _send_challenge(request, user, OtpChallenge.ACTIVATION)
    if error:
        user.email = previous
        user.save(update_fields=['email'])
        return error
    AccountSecurity.objects.create(user=user)
    return _step(challenge)


def _challenge(request):
    data = _body(request)
    if not data or not isinstance(data.get('challengeId'), str):
        return None
    try:
        challenge_id = UUID(data['challengeId'])
    except ValueError:
        return None
    return OtpChallenge.objects.select_related('user').filter(
        pk=challenge_id, session_key=_session_key(request), consumed=False).first()


@require_POST
def verify_view(request):
    data = _body(request)
    code = data.get('code') if data else None
    pending = request.session.get('pending_registration')
    if pending and data and data.get('challengeId') == pending['challenge_id']:
        return _verify_pending_registration(request, pending, code)
    challenge = _challenge(request)
    if (challenge is None or challenge.purpose not in {OtpChallenge.ACTIVATION, OtpChallenge.LOGIN}
            or not isinstance(code, str) or not re.fullmatch(r'\d{6}', code)):
        return _error('Invalid or expired code.')
    if _too_many_attempts(challenge.user):
        return _error('Too many incorrect codes. Try again in 10 minutes.', 429)
    if challenge.expires_at <= timezone.now() or challenge.attempts >= 5:
        return _error('Invalid or expired code.')
    if not check_password(code, challenge.code_hash):
        OtpChallenge.objects.filter(pk=challenge.pk, consumed=False).update(attempts=challenge.attempts + 1)
        return _error('Invalid or expired code.')
    with transaction.atomic():
        challenge = OtpChallenge.objects.select_for_update().get(pk=challenge.pk)
        if challenge.consumed or challenge.expires_at <= timezone.now() or challenge.attempts >= 5:
            return _error('Invalid or expired code.')
        challenge.consumed = True
        challenge.save(update_fields=['consumed'])
        if challenge.purpose == OtpChallenge.ACTIVATION:
            AccountSecurity.objects.update_or_create(user=challenge.user, defaults={'email_verified': True})
            challenge.user.is_active = True
            challenge.user.save(update_fields=['is_active'])
            profile = ensure_profile(challenge.user)
            profile.email = challenge.user.email
            profile.save(update_fields=['email'])
            request.session.pop('pending_email_user', None)
            return JsonResponse({'step': 'login_required', 'detail': 'Email verified. Sign in to continue.'})
        if not AccountSecurity.objects.filter(user=challenge.user, email_verified=True).exists() or not challenge.user.is_active:
            return _error('Account is not verified.', 403)
        login(request, challenge.user, backend='django.contrib.auth.backends.ModelBackend')
        request.session['auth_mfa_user'] = challenge.user.pk
        return JsonResponse({'step': 'authenticated', 'detail': 'Signed in successfully.'})


@require_POST
def resend_view(request):
    data = _body(request)
    pending = request.session.get('pending_registration')
    if pending and data and data.get('challengeId') == pending['challenge_id']:
        now = timezone.now().timestamp()
        if pending['expires_at'] <= now:
            return _error('Invalid or expired code.')
        if pending['last_sent_at'] > now - 60:
            return _error('Please wait before requesting another code.', 429)
        if pending['sent_count'] >= 10 or pending['attempts'] >= 5:
            return _error('Too many codes requested. Try again later.', 429)
        return _send_pending_registration(
            request, pending['username'], pending['email'], pending['password_hash'],
            attempts=pending['attempts'], sent_count=pending['sent_count'],
        )
    challenge = _challenge(request)
    if (challenge is None or challenge.purpose not in {OtpChallenge.ACTIVATION, OtpChallenge.LOGIN}
            or challenge.expires_at <= timezone.now()):
        return _error('Invalid or expired code.')
    if challenge.last_sent_at > timezone.now() - timedelta(seconds=60):
        return _error('Please wait before requesting another code.', 429)
    replacement, error = _send_challenge(request, challenge.user, challenge.purpose)
    return error or _step(replacement)


@require_POST
def password_reset_request_view(request):
    data = _body(request)
    email = _email(data.get('email')) if data else None
    if not email:
        return _error('A valid email address is required.')
    cache_key = f'password-reset:{hashlib.sha256(email.encode()).hexdigest()}'
    if not cache.add(cache_key, True, timeout=60):
        return _error('Please wait one minute before requesting another code.', 429)
    user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
    challenge_id = uuid4()
    if user and AccountSecurity.objects.filter(user=user, email_verified=True).exists():
        challenge, _ = _send_challenge(request, user, OtpChallenge.RESET)
        if challenge:
            challenge_id = challenge.pk
    return JsonResponse({
        'step': 'password_reset', 'challengeId': str(challenge_id), 'retryAfter': 60,
        'detail': 'If an active account uses this email, a reset code has been sent.',
    })


@require_POST
def password_reset_confirm_view(request):
    data = _body(request)
    challenge = _challenge(request)
    code = data.get('code') if data else None
    password = data.get('password') if data else None
    if (challenge is None or challenge.purpose != OtpChallenge.RESET
            or not isinstance(code, str) or not re.fullmatch(r'\d{6}', code)
            or not isinstance(password, str)):
        return _error('Invalid or expired reset code.')
    if _too_many_attempts(challenge.user):
        return _error('Too many incorrect codes. Try again in 10 minutes.', 429)
    if (challenge.expires_at <= timezone.now() or challenge.attempts >= 5
            or not challenge.user.is_active
            or not AccountSecurity.objects.filter(user=challenge.user, email_verified=True).exists()):
        return _error('Invalid or expired reset code.')
    problem = _validate_new_password(password, challenge.user)
    if problem:
        return _error(problem)
    if not check_password(code, challenge.code_hash):
        OtpChallenge.objects.filter(pk=challenge.pk, consumed=False, attempts__lt=5).update(attempts=F('attempts') + 1)
        return _error('Invalid or expired reset code.')
    with transaction.atomic():
        challenge = OtpChallenge.objects.select_for_update().get(pk=challenge.pk)
        if (challenge.consumed or challenge.expires_at <= timezone.now() or challenge.attempts >= 5
                or not challenge.user.is_active):
            return _error('Invalid or expired reset code.')
        user = challenge.user
        user.set_password(password)
        user.save(update_fields=['password'])
        User_profile.objects.filter(user=user).update(password=user.password)
        OtpChallenge.objects.filter(user=user, consumed=False).update(consumed=True)
    logout(request)
    return JsonResponse({'step': 'password_reset_complete', 'detail': 'Password updated. Sign in with your new password.'})

@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({'detail': 'Signed out.'})

def _profile_response(request, profile):
    avatar_url = request.build_absolute_uri(profile.avatar.url) if profile.avatar else ''
    return {
        'id': profile.id,
        'userName': profile.userName,
        'email': '' if profile.email.endswith('@profiles.invalid') else profile.email,
        'avatarUrl': avatar_url,
        'bio': profile.bio,
        'isAdmin': request.user.is_staff or request.user.is_superuser,
    }


@require_http_methods(['GET', 'POST'])
def profile_view(request):
    profile = current_profile(request)
    if profile is None:
        return _error('Profile unavailable. Please sign in.', 404)
    if request.method == 'GET':
        return JsonResponse(_profile_response(request, profile))
    username = request.POST.get('userName', profile.userName).strip()
    bio = request.POST.get('bio', profile.bio)
    password = request.POST.get('password', '')
    avatar = request.FILES.get('avatar')
    if not 3 <= len(username) <= 30:
        return _error('Username must be 3 to 30 characters long.')
    if len(bio) > 300:
        return _error('Bio must be at most 300 characters.')
    if password:
        problem = _validate_new_password(password, request.user)
        if problem:
            return _error(problem)
    if avatar and avatar.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
        return _error('Avatar must be JPG, PNG or WebP.')
    if avatar and avatar.size > 5 * 1024 * 1024:
        return _error('Avatar must be at most 5 MB.')
    if avatar:
        try:
            avatar = sanitize_image(avatar)
        except ValidationError as exc:
            return _error(exc.messages[0])
    profile.userName = username
    profile.bio = bio
    if password:
        request.user.set_password(password)
        request.user.save(update_fields=['password'])
        profile.password = request.user.password
        OtpChallenge.objects.filter(user=request.user, consumed=False).update(consumed=True)
        update_session_auth_hash(request, request.user)
    if avatar:
        profile.avatar = avatar
    profile.save()
    response = _profile_response(request, profile)
    response['message'] = 'Profile updated.'
    return JsonResponse(response)
