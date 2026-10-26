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
    path("stack/<int:pk>/outline/", views.outline, name="outline"),
    path("frame/<int:pk>/visibility/", views.frame_visibility, name="frame_visibility"),
    path("frame/<int:pk>.jpg", views.frame_image, name="frame_image"),
    path("epma/<int:pk>/", views.epma_session, name="epma_session"),
    path("epma/channel/<int:pk>.jpg", views.epma_image, name="epma_image"),
    path("epma/channel/<int:pk>.bin", views.epma_data, name="epma_data"),
]
