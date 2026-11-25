from zipfile import ZipFile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hosting.models import Announcement, Member, Site
from hosting.publishing import publish


class Command(BaseCommand):
    help = "Create demo accounts and publish the sample site in local demo mode."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEMO:
            raise CommandError("This command requires WNBASE_DEMO=1.")
        users = get_user_model().objects
        owner, owner_created = users.get_or_create(username="demo")
        if owner_created:
            owner.set_password("wnbase-demo-local")
            owner.save(update_fields=["password"])
        admin, admin_created = users.get_or_create(
            username="admin", defaults={"is_staff": True, "is_superuser": True},
        )
        if admin_created:
            admin.set_password("wnbase-admin-local")
            admin.save(update_fields=["password"])
        member, _ = Member.objects.get_or_create(user=owner, defaults={"handle": "demo"})
        site, _ = Site.objects.get_or_create(
            owner=member, slug="build-notes", defaults={
                "title": "Build Notes", "description": "A sample site with CSS and browser JavaScript.",
                "listed": True,
            },
        )
        if site.live_id is None:
            with ZipFile(settings.BASE_DIR / "examples/sample-site.zip") as archive:
                publish(site, {name: archive.read(name) for name in archive.namelist()})
        Announcement.objects.get_or_create(
            author=admin, title="Hosting prototype is open", defaults={
                "body": "You can now publish a site from a ZIP and add it to the public directory.",
                "published": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("Demo accounts and sample site are ready."))
