from django.http import JsonResponse


def bad_request(request, exception):
    return JsonResponse({'detail': 'Invalid request.'}, status=400)


def permission_denied(request, exception):
    return JsonResponse({'detail': 'Access denied.'}, status=403)


def not_found(request, exception):
    return JsonResponse({'detail': 'The requested resource was not found.'}, status=404)


def server_error(request):
    return JsonResponse({'detail': 'An unexpected error occurred. Please try again later.'}, status=500)


def csrf_failure(request, reason=''):
    return JsonResponse({'detail': 'Security verification failed. Refresh the page and try again.'}, status=403)
