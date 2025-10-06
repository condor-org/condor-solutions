# apps/common/urls.py

from django.urls import path
from apps.common.views import MonitoreoRecursosView

urlpatterns = [
    path('monitoreo/recursos/', MonitoreoRecursosView.as_view(), name='monitoreo_recursos'),
]
