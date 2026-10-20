from django.db import models


class MediaRole(models.Model):
    """RB-3: one media job, and one column of the schedule table."""

    code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    # RB-3: not called `column`, which is a SQL keyword.
    table_column = models.CharField(max_length=50)
    display_order = models.PositiveIntegerField()

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return self.name


class EventType(models.Model):
    """RB-3: what kind of event it is: a service, prayer or special event."""

    code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Position(models.Model):
    """RB-3: one role, or two roles shared by one person (Sound + ProPresenter)."""

    code = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=100)
    roles = models.ManyToManyField(MediaRole, related_name="positions")

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
