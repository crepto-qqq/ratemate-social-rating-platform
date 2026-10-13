from django.urls import path

from . import views
from . import public_views


app_name = 'rating'

urlpatterns = [
    path('public/', public_views.public_collection_view, name='public-list'),
    path('public/<int:result_id>/', public_views.public_detail_view, name='public-detail'),
    path('public/<int:result_id>/like/', public_views.like_view, name='like'),
    path('public/<int:result_id>/comments/', public_views.comment_collection_view, name='comments'),
    path('public/<int:result_id>/comments/<int:comment_id>/', public_views.comment_detail_view, name='comment-detail'),
    path('', views.rating_collection_view, name='collection'),
    path('<int:result_id>/', views.rating_detail_view, name='detail'),
]
