from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/<int:pk>/', views.post_details, name='post_details')
    # path('pl/', views.post_list_2, name='post_list_2'),
]