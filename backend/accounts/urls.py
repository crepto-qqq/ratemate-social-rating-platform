from django.urls import path

from . import views


app_name = 'accounts'

urlpatterns = [
    path('csrf/', views.csrf_view, name='csrf'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
]
