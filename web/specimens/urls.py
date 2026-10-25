from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("starred/", views.starred, name="starred"),
    path("slab/<str:slab_no>/", views.slab, name="slab"),
    path("stack/<int:pk>/", views.stack, name="stack"),
    path("stack/<int:pk>/split/", views.split_stack, name="split_stack"),
    path("stack/<int:pk>/merge/", views.merge_stack, name="merge_stack"),
    path("stack/<int:pk>/delete/", views.delete_stack, name="delete_stack"),
    path("stack/<int:pk>/restore/", views.restore_stack, name="restore_stack"),
    path("frame/<int:pk>/visibility/", views.frame_visibility, name="frame_visibility"),
    path("frame/<int:pk>.jpg", views.frame_image, name="frame_image"),
]
