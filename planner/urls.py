from django.urls import path
from . import views

urlpatterns = [
    path("api/route/", views.route_api, name="route-api"),
    path("", views.map_page, name="map"),
]
