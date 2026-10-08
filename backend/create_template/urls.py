from django.urls import path

from . import views


app_name = 'create_template'

urlpatterns = [
    path('', views.create_template_view, name='create'),
    path('favorites/', views.favorite_list_view, name='favorite-list'),
    path('<int:template_id>/favorite/', views.favorite_detail_view, name='favorite-detail'),
]
