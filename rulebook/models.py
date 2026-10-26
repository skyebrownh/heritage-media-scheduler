from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from rulebook.dates import nth_in_month, ranges_overlap


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


class Team(models.Model):
    """RB-4: a group of volunteers. Rotating teams take turns by week."""

    name = models.CharField(max_length=100, unique=True)
    rotates = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField()

    class Meta:
        ordering = ["display_order"]

    def __str__(self):
        return self.name


class EffectiveDatedQuerySet(models.QuerySet):
    def in_force_on(self, day):
        """RB-7: the rows that applied on this date. Both ends are inclusive."""
        return self.filter(effective_from__lte=day).filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=day)
        )


class EffectiveDated(models.Model):
    """RB-7: a rule with effective dates, so a lookup can ask "what applied on this date?".

    Rules are never edited in place for past dates: a change ends the old row and adds
    a new one. Each table names its key fields, and no two rows with the same key may
    cover the same day, so a date never has two answers.
    """

    # The fields that say two rows are versions of the same rule, e.g. (weekday, nth).
    key_fields = ()

    effective_from = models.DateField()
    # Inclusive. Empty means the rule has no end.
    effective_until = models.DateField(null=True, blank=True)

    objects = EffectiveDatedQuerySet.as_manager()

    class Meta:
        abstract = True
        constraints = [
            models.CheckConstraint(
                condition=Q(effective_until__isnull=True)
                | Q(effective_until__gte=F("effective_from")),
                name="%(app_label)s_%(class)s_until_not_before_from",
            )
        ]

    def clean(self):
        super().clean()
        # A missing date or key is already reported by its own field's error.
        if self.effective_from is None or any(
            getattr(self, name) is None for name in self.key_fields
        ):
            return
        if self.effective_until is not None and self.effective_until < self.effective_from:
            raise ValidationError(
                {"effective_until": "The end date can't be before the start date."}
            )
        same_rule = {name: getattr(self, name) for name in self.key_fields}
        for other in type(self).objects.filter(**same_rule).exclude(pk=self.pk):
            if ranges_overlap(
                self.effective_from, self.effective_until,
                other.effective_from, other.effective_until,
            ):
                raise ValidationError(
                    "These dates overlap another rule for the same weekday and week "
                    f"({other.effective_from} to {other.effective_until or 'no end'})."
                )


class RotationRule(EffectiveDated):
    """RB-5: which rotating team is on for the nth weekday of a month, from a date."""

    key_fields = ("weekday", "nth")

    WEEKDAYS = [
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
        (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ]

    weekday = models.PositiveSmallIntegerField(choices=WEEKDAYS)
    nth = models.PositiveSmallIntegerField(help_text="1 for the first, 2 for the second, and so on.")
    # PROTECT: deleting a team would silently erase the rules that name it.
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="rotation_rules")

    class Meta(EffectiveDated.Meta):
        ordering = ["weekday", "nth", "effective_from"]
        constraints = [
            *EffectiveDated.Meta.constraints,
            models.CheckConstraint(
                condition=Q(weekday__gte=0, weekday__lte=6), name="rotationrule_weekday_0_to_6"
            ),
            models.CheckConstraint(
                condition=Q(nth__gte=1, nth__lte=5), name="rotationrule_nth_1_to_5"
            ),
        ]

    def __str__(self):
        return f"{self.get_weekday_display()} #{self.nth} \u2192 {self.team}"

    def clean(self):
        super().clean()
        if self.team_id is not None and not self.team.rotates:
            raise ValidationError({"team": "Only a team that rotates can have a rotation rule."})

    @classmethod
    def team_on(cls, day):
        """RB-5, RB-7: the team on for this date, or None (e.g. a 5th week).

        Takes only the date and works out the weekday and nth itself, so a caller
        can't pass values that disagree with the date.
        """
        rule = (
            cls.objects.in_force_on(day)
            .filter(weekday=day.weekday(), nth=nth_in_month(day))
            .select_related("team")
            .first()
        )
        return rule.team if rule else None
