from django.contrib import admin

from .models import Announcement, Deployment, Member, Site


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "slug", "listed", "suspended")
    list_filter = ("listed", "suspended")
    search_fields = ("title", "owner__handle", "slug")
    readonly_fields = ("owner", "slug")
    actions = ("suspend_sites", "restore_sites")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Suspend selected sites", permissions=["change"])
    def suspend_sites(self, request, queryset):
        queryset.update(suspended=True)

    @admin.action(description="Restore selected sites", permissions=["change"])
    def restore_sites(self, request, queryset):
        queryset.update(suspended=False)


@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ("site", "created", "size")
    readonly_fields = ("site", "created", "size")

    def has_add_permission(self, request):
        return False


admin.site.register(Member)
admin.site.register(Announcement)
admin.site.site_header = "WNBase administration"
