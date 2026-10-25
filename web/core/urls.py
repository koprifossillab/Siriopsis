from django.urls import path

from . import views

urlpatterns = [
    path("healthz", views.healthz, name="healthz"),
    path("system/", views.system, name="system"),
    path("splash/<str:name>", views.splash_asset, name="splash_asset"),
]
