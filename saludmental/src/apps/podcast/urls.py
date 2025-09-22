from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='podcast_index'),
]
