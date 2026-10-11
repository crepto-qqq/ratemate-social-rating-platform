from django.urls import path

from . import views
from . import comment_views


app_name = 'create_template'

urlpatterns = [
    path('', views.create_template_view, name='create'),
    path('favorites/', views.favorite_list_view, name='favorite-list'),
    path('<int:template_id>/', views.template_detail_view, name='detail'),
    path('<int:template_id>/favorite/', views.favorite_detail_view, name='favorite-detail'),
    path('<int:template_id>/comments/', comment_views.comment_collection_view, name='comment-list'),
    path('<int:template_id>/comments/<int:comment_id>/', comment_views.comment_detail_view, name='comment-detail'),
]
