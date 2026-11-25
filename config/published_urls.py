from django.urls import path

from hosting.views import published_asset

urlpatterns = [
    path("<slug:handle>/<slug:slug>/", published_asset),
    path("<slug:handle>/<slug:slug>/<path:asset>", published_asset),
]
