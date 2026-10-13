from django.urls import path

from . import views


app_name = 'notifications'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('unread-count/', views.unread_count_view, name='unread-count'),
    path('read-all/', views.mark_all_read_view, name='read-all'),
    path('<int:notification_id>/read/', views.mark_read_view, name='read'),
]
