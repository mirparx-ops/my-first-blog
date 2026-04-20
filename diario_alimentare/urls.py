from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('diario/', views.diario_list, name='diario_list'),
    path('pasto/new/',views.pasto_new, name='pasto_new'),
    path('diario/pdf/', views.stampa_pdf, name='stampa_pdf'),
]
