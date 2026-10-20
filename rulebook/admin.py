from django.contrib import admin
from unfold.admin import ModelAdmin

from rulebook.models import EventType, MediaRole, Position


class CodeReadOnlyOnceSaved(ModelAdmin):
    """Other tables will refer to a row by its code, so changing it would orphan them."""

    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), *(["code"] if obj else []))


@admin.register(MediaRole)
class MediaRoleAdmin(CodeReadOnlyOnceSaved):
    list_display = ["name", "code", "table_column", "display_order", "is_active"]


@admin.register(EventType)
class EventTypeAdmin(CodeReadOnlyOnceSaved):
    list_display = ["name", "code"]


@admin.register(Position)
class PositionAdmin(CodeReadOnlyOnceSaved):
    list_display = ["name", "code"]
