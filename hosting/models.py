from django.conf import settings
from django.db import models


class Member(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    handle = models.SlugField(max_length=64, unique=True)
    clerk_id = models.CharField(max_length=80, unique=True, null=True, blank=True)

    def __str__(self):
        return self.handle


class Site(models.Model):
    owner = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="sites")
    slug = models.SlugField(max_length=48)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=240, blank=True)
    listed = models.BooleanField(default=False)
    live = models.ForeignKey("Deployment", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", editable=False)
    suspended = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "slug"], name="one_site_slug_per_member")]

    @property
    def public_url(self):
        return f"{settings.PUBLISH_ORIGIN}/{self.owner.handle}/{self.slug}/"

    def __str__(self):
        return f"{self.owner}/{self.slug}"


class Deployment(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name="deployments")
    created = models.DateTimeField(auto_now_add=True)
    size = models.PositiveIntegerField()

    class Meta:
        ordering = ["-pk"]


class Asset(models.Model):
    deployment = models.ForeignKey(Deployment, on_delete=models.CASCADE, related_name="assets")
    path = models.CharField(max_length=240)
    content = models.BinaryField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["deployment", "path"], name="one_asset_per_deployment_path")]


class Announcement(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    title = models.CharField(max_length=120)
    body = models.TextField()
    published = models.BooleanField(default=False)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]

    def __str__(self):
        return self.title
