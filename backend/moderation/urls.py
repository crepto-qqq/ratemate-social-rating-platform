from django.urls import path

from . import views


urlpatterns = [
    path('me/', views.me_view),
    path('users/', views.users_view),
    path('templates/', views.templates_view),
    path('templates/<int:template_id>/', views.template_detail_view),
    path('ratings/', views.ratings_view),
    path('ratings/<int:rating_id>/', views.rating_detail_view),
    path('comments/', views.comments_view),
    path('actions/', views.actions_view),
    path('templates/<int:template_id>/hide/', views.hide_template_view),
    path('templates/<int:template_id>/restore/', views.restore_template_view),
    path('ratings/<int:rating_id>/remove/', views.remove_rating_view),
    path('comments/template/<int:comment_id>/remove/', views.remove_template_comment_view),
    path('comments/rating/<int:comment_id>/remove/', views.remove_rating_comment_view),
]
