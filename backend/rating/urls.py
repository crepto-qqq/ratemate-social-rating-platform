from django.urls import path

from . import views


app_name = 'rating'

urlpatterns = [
    path('', views.rating_collection_view, name='collection'),
    path('<int:result_id>/', views.rating_detail_view, name='detail'),
]
