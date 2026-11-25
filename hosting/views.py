import re
from pathlib import PurePosixPath
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.forms import BooleanField, CharField, FileField, Form, RegexField, Textarea
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_safe

from .models import Announcement, Asset, Member, Site
from .publishing import TYPES, assets_from_zip, publish

SLUG = r"^[a-z0-9]+(?:-[a-z0-9]+)*\Z"
MAX_SITES = 3
RESERVED_HANDLES = {"admin", "announcements", "workspace", "static", "healthz", "sign-in", "demo-login", "demo-logout"}


class HandleForm(Form):
    handle = RegexField(SLUG, max_length=32, help_text="Lowercase letters, numbers, and hyphens.")


class SiteForm(Form):
    title = CharField(max_length=100)
    slug = RegexField(SLUG, max_length=48, label="URL name")
    description = CharField(max_length=240, required=False, widget=Textarea(attrs={"rows": 3}))
    listed = BooleanField(required=False, label="Show in the public directory")


class UploadForm(Form):
    archive = FileField(label="Site ZIP")


class AnnouncementForm(Form):
    title = CharField(max_length=120)
    body = CharField(max_length=5000, widget=Textarea(attrs={"rows": 6}))
    published = BooleanField(required=False, label="Publish to the public dashboard")


def page(request, template, **context):
    return render(request, f"hosting/{template}.html", {
        "clerk_issuer": settings.CLERK_ISSUER,
        "clerk_key": settings.CLERK_PUBLISHABLE_KEY,
        "demo": settings.DEMO,
        "publish_host": settings.PUBLISH_HOST,
        "upload_limit": settings.WNBASE_SITE_LIMIT_MIB,
        "file_limit": settings.WNBASE_SITE_FILE_LIMIT,
        **context,
    })


def dashboard(request):
    sites = Site.objects.filter(listed=True, suspended=False, live__isnull=False).select_related("owner", "live")
    return page(request, "dashboard", sites=sites.order_by("-live__created"),
                announcements=Announcement.objects.filter(published=True)[:8])


def sign_in(request):
    if request.user.is_authenticated:
        return redirect("workspace")
    return page(request, "sign_in")


@login_required
def workspace(request):
    member = Member.objects.filter(user=request.user).first()
    if member is None and hasattr(request, "clerk_subject"):
        username = request.clerk_username
        if not isinstance(username, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", username):
            return page(request, "account", problem="Set a username in your Clerk account, then reload this page.")
        if settings.APP_HOST == settings.PUBLISH_HOST and username.lower() in RESERVED_HANDLES:
            return page(request, "account", problem="Choose a different username in Clerk. This one is reserved by WNBase.")
        try:
            member, _ = Member.objects.get_or_create(
                user=request.user, defaults={"handle": username, "clerk_id": request.clerk_subject},
            )
        except IntegrityError:
            return page(request, "account", problem="That username is already reserved by a WNBase account.")
    if member is None:
        if not settings.DEMO:
            return page(request, "account", problem="Sign in through Clerk to create a hosting account.")
        form = HandleForm(request.POST if request.method == "POST" else None)
        if form.is_valid():
            try:
                Member.objects.create(user=request.user, handle=form.cleaned_data["handle"])
            except IntegrityError:
                form.add_error("handle", "That username is unavailable.")
            else:
                return redirect("workspace")
        return page(request, "form", title="Choose your username", form=form, action="Save username",
                    description="Your username becomes the first part of your published site URLs.")
    return page(request, "workspace", member=member, sites=member.sites.select_related("owner", "live"),
                can_create=member.sites.count() < MAX_SITES)


@login_required
def new_site(request):
    member = Member.objects.filter(user=request.user).first()
    if member is None:
        return redirect("workspace")
    form = SiteForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        with transaction.atomic():
            member = Member.objects.select_for_update().get(pk=member.pk)
            if member.sites.count() >= MAX_SITES:
                form.add_error(None, "Each account can host three sites.")
            else:
                site, created = member.sites.get_or_create(
                    slug=form.cleaned_data["slug"],
                    defaults={key: value for key, value in form.cleaned_data.items() if key != "slug"},
                )
                if created:
                    return redirect("site", pk=site.pk)
                form.add_error("slug", "You already have a site at this URL.")
    return page(request, "form", title="Create a site", form=form, action="Create site",
                description=f"Your site will publish under {settings.PUBLISH_HOST}/{member.handle}/.")


@login_required
def manage_site(request, pk):
    site = get_object_or_404(Site.objects.select_related("owner", "live"), pk=pk, owner__user=request.user)
    form = UploadForm(request.POST if request.method == "POST" else None, request.FILES)
    if form.is_valid():
        try:
            publish(site, assets_from_zip(form.cleaned_data["archive"]))
        except ValidationError as exc:
            form.add_error("archive", exc)
        else:
            messages.success(request, "Site published.", extra_tags="deployment")
            return redirect("site", pk=site.pk)
    return page(request, "site", site=site, form=form, deployments=site.deployments.all())


@login_required
def site_settings(request, pk):
    site = get_object_or_404(Site, pk=pk, owner__user=request.user)
    form = SiteForm(request.POST if request.method == "POST" else None, initial={
        "title": site.title, "slug": site.slug, "description": site.description, "listed": site.listed,
    })
    del form.fields["slug"]
    if form.is_valid():
        for field, value in form.cleaned_data.items():
            setattr(site, field, value)
        site.save(update_fields=list(form.cleaned_data))
        return redirect("site", pk=site.pk)
    return page(request, "form", title="Site settings", form=form, action="Save settings")


@login_required
@permission_required("hosting.add_announcement", raise_exception=True)
def new_announcement(request):
    form = AnnouncementForm(request.POST if request.method == "POST" else None)
    if form.is_valid():
        Announcement.objects.create(author=request.user, **form.cleaned_data)
        return redirect("announcements")
    return page(request, "form", title="New announcement", form=form, action="Save announcement")


@login_required
@permission_required("hosting.change_announcement", raise_exception=True)
def announcements(request):
    return page(request, "announcements", announcements=Announcement.objects.all())


@login_required
@permission_required("hosting.change_announcement", raise_exception=True)
def edit_announcement(request, pk):
    item = get_object_or_404(Announcement, pk=pk)
    form = AnnouncementForm(request.POST if request.method == "POST" else None, initial={
        "title": item.title, "body": item.body, "published": item.published,
    })
    if form.is_valid():
        for field, value in form.cleaned_data.items():
            setattr(item, field, value)
        item.save(update_fields=[*form.cleaned_data, "updated"])
        return redirect("announcements")
    return page(request, "form", title="Edit announcement", form=form, action="Save announcement")


@require_safe
def published_frame(request, handle, slug, asset=""):
    site = get_object_or_404(
        Site.objects.select_related("owner"),
        owner__handle=handle, slug=slug, suspended=False, live__isnull=False,
    )
    path = asset if asset and not asset.endswith("/") else asset + "index.html"
    get_object_or_404(Asset.objects.only("id"), deployment_id=site.live_id, path=path)
    source = f"{settings.CONTENT_ORIGIN}/{handle}/{slug}/{quote(asset)}"
    if query := request.META.get("QUERY_STRING"):
        source += "?" + query
    mime = TYPES[PurePosixPath(path).suffix.lower()]
    if not mime.startswith("text/html"):
        return redirect(source)
    response = render(request, "hosting/published_frame.html", {"site": site, "source": source})
    response["Content-Security-Policy"] = (
        "default-src 'none'; style-src 'unsafe-inline'; "
        f"frame-src {settings.CONTENT_ORIGIN}; frame-ancestors 'none'; base-uri 'none'"
    )
    response["Cache-Control"] = "no-cache"
    return response


@require_safe
@xframe_options_exempt
def published_asset(request, handle, slug, asset=""):
    path = asset if asset and not asset.endswith("/") else asset + "index.html"
    item = get_object_or_404(
        Asset.objects.filter(deployment__site__owner__handle=handle, deployment__site__slug=slug,
                             deployment__site__suspended=False, deployment__site__live_id=F("deployment_id")),
        path=path,
    )
    mime = TYPES[PurePosixPath(path).suffix.lower()]
    content = bytes(item.content)
    response = media_response(request, content, mime) if mime.startswith(("video/", "audio/")) else HttpResponse(content, content_type=mime)
    response["Content-Security-Policy"] = (
        "sandbox allow-scripts allow-forms; object-src 'none'; base-uri 'none'; "
        "worker-src 'none'; form-action https: http:; "
        f"frame-ancestors {settings.APP_ORIGIN}"
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Referrer-Policy"] = "no-referrer"
    response["Access-Control-Allow-Origin"] = "*"
    response["Cache-Control"] = "no-cache"
    return response


def media_response(request, content, mime):
    size = len(content)
    requested = re.fullmatch(r"bytes=([0-9]{0,18})-([0-9]{0,18})", request.headers.get("Range", ""))
    if not requested or not any(requested.groups()) or request.method != "GET" or request.headers.get("If-Range"):
        response = HttpResponse(content, content_type=mime)
        response["Content-Length"] = size
    else:
        first, last = requested.groups()
        start = int(first) if first else max(0, size - int(last))
        end = min(int(last), size - 1) if first and last else size - 1
        if start > end:
            response = HttpResponse(status=416)
            response["Content-Range"] = f"bytes */{size}"
        else:
            response = HttpResponse(content[start:end + 1], content_type=mime, status=206)
            response["Content-Range"] = f"bytes {start}-{end}/{size}"
            response["Content-Length"] = end - start + 1
    response["Accept-Ranges"] = "bytes"
    return response
