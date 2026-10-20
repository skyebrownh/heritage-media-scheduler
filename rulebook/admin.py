from django import forms
from django.contrib import admin
from unfold.admin import ModelAdmin

from rulebook.models import EventType, MediaRole, Position


class CodeReadOnlyOnceSaved(ModelAdmin):
    """RB-3: other tables will refer to a row by its code, so changing it would orphan them."""

    def get_readonly_fields(self, request, obj=None):
        return (*super().get_readonly_fields(request, obj), *(["code"] if obj else []))


@admin.register(MediaRole)
class MediaRoleAdmin(CodeReadOnlyOnceSaved):
    list_display = ["name", "code", "table_column", "display_order", "is_active"]


@admin.register(EventType)
class EventTypeAdmin(CodeReadOnlyOnceSaved):
    list_display = ["name", "code"]


class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = ["code", "name", "roles"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # RB-3: skip Django's generic "required" message so clean_roles gives one message
        # for both too few and too many.
        self.fields["roles"].required = False

    def clean_roles(self):
        # RB-3: checked here, not in save(), because a many-to-many only exists
        # after the position itself is saved.
        roles = self.cleaned_data["roles"]
        if not 1 <= len(roles) <= 2:
            raise forms.ValidationError(
                "A position needs one or two roles (two when one person shares them)."
            )
        return roles


@admin.register(Position)
class PositionAdmin(CodeReadOnlyOnceSaved):
    form = PositionForm
    list_display = ["name", "code"]
