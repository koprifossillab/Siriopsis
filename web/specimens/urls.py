from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("slab/<str:slab_no>/", views.slab, name="slab"),
    path("stack/<int:pk>/", views.stack, name="stack"),
    path("frame/<int:pk>.jpg", views.frame_image, name="frame_image"),
]
