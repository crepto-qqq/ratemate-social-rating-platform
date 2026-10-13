from django.urls import path

from . import views


app_name = 'accounts'

urlpatterns = [
    path('csrf/', views.csrf_view, name='csrf'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('enroll-email/', views.enroll_email_view, name='enroll-email'),
    path('verify/', views.verify_view, name='verify'),
    path('resend/', views.resend_view, name='resend'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
