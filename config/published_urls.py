from django.conf import settings
from django.urls import path

from django.views.generic import RedirectView

from hosting.views import published_asset

urlpatterns = [
    path("", RedirectView.as_view(url=settings.APP_ORIGIN + "/")),
    path("<slug:handle>/<slug:slug>/", published_asset),
    path("<slug:handle>/<slug:slug>/<path:asset>", published_asset),
]
