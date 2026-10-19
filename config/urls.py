from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView

from config import views

urlpatterns = [
    path("health/", views.health),
    path("admin/", admin.site.urls),
    # The admin is the only interface, so the front door just leads to it.
    path("", RedirectView.as_view(url="/admin/")),
]
