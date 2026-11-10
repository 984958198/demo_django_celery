from django.urls import path
from demoapp import views

urlpatterns = [
    path('instances/', views.InstanceView.as_view(), name='instances'),
    path('instances/tcp/', views.tcp, name='instances_tcp'),
]
