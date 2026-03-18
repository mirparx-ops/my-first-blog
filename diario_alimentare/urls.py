from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('diario/', views.diario_list, name='diario_list'),
]
