from django.urls import path

from . import views

urlpatterns = [
    path('tvwebhook', views.tvwebhook, name='tvwebhook'),
    path('qbwebhook', views.qbwebhook, name='qbwebhook'),
]
