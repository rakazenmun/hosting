from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse
from django.urls import path

from hosting import views

def health(request):
    return HttpResponse("ok", content_type="text/plain")


urlpatterns = [
    path("healthz/", health, name="health"),
    path("", views.dashboard, name="dashboard"),
    path("sign-in/", views.sign_in, name="sign-in"),
    path("workspace/", views.workspace, name="workspace"),
    path("workspace/new/", views.new_site, name="new-site"),
    path("workspace/sites/<int:pk>/", views.manage_site, name="site"),
    path("workspace/sites/<int:pk>/settings/", views.site_settings, name="site-settings"),
    path("announcements/", views.announcements, name="announcements"),
    path("announcements/new/", views.new_announcement, name="new-announcement"),
    path("announcements/<int:pk>/", views.edit_announcement, name="edit-announcement"),
    path("admin/", admin.site.urls),
]
if settings.DEMO:
    urlpatterns += [
        path("demo-login/", LoginView.as_view(template_name="hosting/demo_login.html"), name="demo-login"),
        path("demo-logout/", LogoutView.as_view(next_page="dashboard"), name="demo-logout"),
    ]
