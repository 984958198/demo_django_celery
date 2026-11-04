
from django.contrib import admin
from django.urls import path, include
from mysite import views


urlpatterns = [
    path('api/instances/', views.InstanceView.as_view(), name='instance'),
    path('api/instances/tcp/', views.tcp, name='instances_tcp'),
]
