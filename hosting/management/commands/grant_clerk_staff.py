from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Grant a signed-in Clerk account announcement and site moderation permissions."

    def add_arguments(self, parser):
        parser.add_argument("clerk_user_id")

    def handle(self, *args, **options):
        if not settings.CLERK_ISSUER:
            raise CommandError("Configure Clerk first.")
        user = get_user_model().objects.filter(username=f"clerk:{options['clerk_user_id']}").first()
        if user is None:
            raise CommandError("The Clerk user must sign in to WNBase first.")
        user.is_staff = True
        user.save(update_fields=["is_staff"])
        user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label="hosting",
            codename__in=("add_announcement", "change_announcement", "view_announcement", "view_site", "change_site"),
        ))
        self.stdout.write(self.style.SUCCESS("Granted announcement and site moderation permissions."))
