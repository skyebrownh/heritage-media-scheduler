import importlib

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from datetime import date

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from rulebook.dates import nth_in_month, ranges_overlap
from rulebook.models import EventType, MediaRole, Position, RotationRule, Team


class AdminTestCase(TestCase):
    """RB-3: logs in a fictional superuser, since the admin is the only interface."""

    def setUp(self):
        User.objects.create_superuser("jane", password="pw-for-tests")
        self.client.login(username="jane", password="pw-for-tests")


class MediaRoleAdminTests(AdminTestCase):
    """RB-3: Skye can add, edit and list media roles in the admin."""

    def test_add_a_role_with_all_five_fields(self):
        response = self.client.post(
            reverse("admin:rulebook_mediarole_add"),
            {
                "code": "test_role",
                "name": "Test role",
                "is_active": "on",
                "table_column": "Test",
                "display_order": 99,
            },
        )
        self.assertRedirects(response, reverse("admin:rulebook_mediarole_changelist"))
        role = MediaRole.objects.get(code="test_role")
        self.assertEqual(
            (role.name, role.is_active, role.table_column, role.display_order),
            ("Test role", True, "Test", 99),
        )

    def test_edit_a_role(self):
        MediaRole.objects.create(
            code="test_role", name="Old", table_column="Old", display_order=1
        )
        response = self.client.post(
            reverse("admin:rulebook_mediarole_change", args=["test_role"]),
            {"name": "New", "table_column": "New", "display_order": 2},
        )
        self.assertRedirects(response, reverse("admin:rulebook_mediarole_changelist"))
        role = MediaRole.objects.get(code="test_role")
        # Unticked is_active is saved as False.
        self.assertEqual((role.name, role.table_column, role.display_order, role.is_active), ("New", "New", 2, False))

    def test_list_shows_roles(self):
        MediaRole.objects.create(
            code="test_role", name="Listed role", table_column="T", display_order=1
        )
        response = self.client.get(reverse("admin:rulebook_mediarole_changelist"))
        self.assertContains(response, "Listed role")

    def test_code_of_an_existing_role_cannot_be_changed(self):
        MediaRole.objects.create(
            code="test_role", name="Role", table_column="T", display_order=1
        )
        self.client.post(
            reverse("admin:rulebook_mediarole_change", args=["test_role"]),
            {"code": "other_code", "name": "Role", "table_column": "T", "display_order": 1},
        )
        self.assertTrue(MediaRole.objects.filter(code="test_role").exists())
        self.assertFalse(MediaRole.objects.filter(code="other_code").exists())

    def test_anonymous_visitor_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("admin:rulebook_mediarole_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])


class EventTypeAdminTests(AdminTestCase):
    """RB-3: Skye can add and edit event types in the admin."""

    def test_add_and_edit_an_event_type(self):
        self.client.post(
            reverse("admin:rulebook_eventtype_add"),
            {"code": "test_type", "name": "Test type"},
        )
        self.assertEqual(EventType.objects.get(code="test_type").name, "Test type")
        self.client.post(
            reverse("admin:rulebook_eventtype_change", args=["test_type"]),
            {"name": "Renamed"},
        )
        self.assertEqual(EventType.objects.get(code="test_type").name, "Renamed")


class PositionAdminTests(AdminTestCase):
    """RB-3: a position covers one role, or two roles shared by one person."""

    def setUp(self):
        super().setUp()
        for order, code in enumerate(["role_a", "role_b", "role_c"]):
            MediaRole.objects.create(
                code=code, name=code, table_column=code, display_order=order
            )

    def add_position(self, roles):
        return self.client.post(
            reverse("admin:rulebook_position_add"),
            {"code": "test_position", "name": "Test position", "roles": roles},
        )

    def test_saves_with_one_role(self):
        self.add_position(["role_a"])
        position = Position.objects.get(code="test_position")
        self.assertEqual([r.code for r in position.roles.all()], ["role_a"])

    def test_saves_with_two_roles(self):
        self.add_position(["role_a", "role_b"])
        position = Position.objects.get(code="test_position")
        self.assertEqual(position.roles.count(), 2)

    def test_rejects_no_roles(self):
        response = self.add_position([])
        self.assertContains(response, "one or two roles")
        self.assertFalse(Position.objects.filter(code="test_position").exists())

    def test_rejects_three_roles(self):
        response = self.add_position(["role_a", "role_b", "role_c"])
        self.assertContains(response, "one or two roles")
        self.assertFalse(Position.objects.filter(code="test_position").exists())


class SeedTests(TestCase):
    """RB-3: a data migration adds the codes SPEC.md names."""

    def test_media_roles_are_seeded_in_column_order(self):
        roles = MediaRole.objects.values_list("code", "table_column", "display_order")
        self.assertEqual(
            list(roles),
            [
                ("propresenter", "ProPresenter", 1),
                ("sound", "Sound", 2),
                ("camera_director", "Director", 3),
                ("main_camera_1", "Main 1", 4),
                ("main_camera_2", "Main 2", 5),
                ("mobile_camera_3", "Mobile 3", 6),
                ("on_call", "On Call", 7),
            ],
        )

    def test_each_role_has_a_single_role_position(self):
        for role in MediaRole.objects.all():
            position = Position.objects.get(code=role.code)
            self.assertEqual(list(position.roles.all()), [role])

    def test_sound_propresenter_shares_two_roles(self):
        position = Position.objects.get(code="sound_propresenter")
        self.assertEqual(position.name, "Sound + ProPresenter")
        self.assertEqual(
            sorted(r.code for r in position.roles.all()), ["propresenter", "sound"]
        )

    def test_event_types_are_seeded(self):
        self.assertEqual(
            dict(EventType.objects.values_list("code", "name")),
            {"service": "Service", "prayer": "Prayer", "special_event": "Special event"},
        )

    def test_running_the_seed_again_adds_no_duplicates(self):
        before = (MediaRole.objects.count(), Position.objects.count(), EventType.objects.count())
        migration = importlib.import_module("rulebook.migrations.0002_seed_rulebook_codes")
        migration.seed(django_apps, None)
        after = (MediaRole.objects.count(), Position.objects.count(), EventType.objects.count())
        self.assertEqual(before, after)
        self.assertEqual(Position.objects.get(code="sound_propresenter").roles.count(), 2)

    def test_running_the_seed_again_keeps_roles_skye_removed_from_a_position(self):
        position = Position.objects.get(code="sound_propresenter")
        position.roles.remove("propresenter")
        migration = importlib.import_module("rulebook.migrations.0002_seed_rulebook_codes")
        migration.seed(django_apps, None)
        self.assertEqual([r.code for r in position.roles.all()], ["sound"])


class RemainingAdminBehaviourTests(AdminTestCase):
    """RB-3: the plan's admin behaviours for event types and positions, not just roles."""

    def setUp(self):
        super().setUp()
        for order, code in enumerate(["role_a", "role_b"]):
            MediaRole.objects.create(
                code=code, name=code, table_column=code, display_order=order
            )

    def test_event_type_list_shows_event_types(self):
        EventType.objects.create(code="test_type", name="Listed type")
        response = self.client.get(reverse("admin:rulebook_eventtype_changelist"))
        self.assertContains(response, "Listed type")

    def test_edit_a_position_and_change_its_roles(self):
        position = Position.objects.create(code="test_position", name="Old")
        position.roles.add("role_a")
        self.client.post(
            reverse("admin:rulebook_position_change", args=["test_position"]),
            {"name": "New", "roles": ["role_a", "role_b"]},
        )
        position.refresh_from_db()
        self.assertEqual(position.name, "New")
        self.assertEqual(position.roles.count(), 2)

    def test_code_of_an_existing_event_type_cannot_be_changed(self):
        EventType.objects.create(code="test_type", name="Type")
        self.client.post(
            reverse("admin:rulebook_eventtype_change", args=["test_type"]),
            {"code": "other_code", "name": "Type"},
        )
        self.assertTrue(EventType.objects.filter(code="test_type").exists())
        self.assertFalse(EventType.objects.filter(code="other_code").exists())

    def test_code_of_an_existing_position_cannot_be_changed(self):
        position = Position.objects.create(code="test_position", name="Position")
        position.roles.add("role_a")
        self.client.post(
            reverse("admin:rulebook_position_change", args=["test_position"]),
            {"code": "other_code", "name": "Position", "roles": ["role_a"]},
        )
        self.assertTrue(Position.objects.filter(code="test_position").exists())
        self.assertFalse(Position.objects.filter(code="other_code").exists())

    def test_anonymous_visitor_cannot_reach_event_type_or_position_pages(self):
        self.client.logout()
        for name in ["rulebook_eventtype_changelist", "rulebook_position_changelist"]:
            response = self.client.get(reverse(f"admin:{name}"))
            self.assertEqual(response.status_code, 302)
            self.assertIn("/admin/login/", response["Location"])


class DateHelperTests(SimpleTestCase):
    """RB-5, RB-7: the plain-Python helpers behind every dated rule."""

    def test_nth_in_month_counts_the_weekday_occurrence(self):
        # 2026-11-01 is the 1st Sunday; 2026-11-29 is the 5th.
        for day, nth in [(1, 1), (7, 1), (8, 2), (14, 2), (15, 3), (22, 4), (28, 4), (29, 5), (30, 5)]:
            with self.subTest(day=day):
                self.assertEqual(nth_in_month(date(2026, 11, day)), nth)

    def test_ranges_overlap_is_inclusive_at_both_ends(self):
        # Touching on one day (a ends the day b starts) is an overlap.
        self.assertTrue(ranges_overlap(date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31), None))
        # The day after is not.
        self.assertFalse(ranges_overlap(date(2026, 1, 1), date(2026, 1, 30), date(2026, 1, 31), None))

    def test_open_ended_range_overlaps_anything_later(self):
        self.assertTrue(ranges_overlap(date(2025, 8, 1), None, date(2030, 1, 1), date(2030, 2, 1)))
        self.assertFalse(ranges_overlap(date(2025, 8, 1), None, date(2024, 1, 1), date(2025, 7, 31)))

    def test_two_open_ended_ranges_always_overlap(self):
        self.assertTrue(ranges_overlap(date(2025, 1, 1), None, date(2030, 1, 1), None))

    def test_ranges_overlap_is_symmetric(self):
        a = (date(2026, 1, 1), date(2026, 3, 1))
        b = (date(2026, 2, 1), None)
        self.assertEqual(ranges_overlap(*a, *b), ranges_overlap(*b, *a))


class TeamAdminTests(AdminTestCase):
    """RB-4: Skye can add and edit teams, and say which ones rotate."""

    def test_add_a_team_with_name_rotates_and_order(self):
        response = self.client.post(
            reverse("admin:rulebook_team_add"),
            {"name": "Test team", "rotates": "on", "display_order": 9},
        )
        self.assertRedirects(response, reverse("admin:rulebook_team_changelist"))
        team = Team.objects.get(name="Test team")
        self.assertEqual((team.rotates, team.display_order), (True, 9))

    def test_edit_a_team(self):
        team = Team.objects.create(name="Old", rotates=True, display_order=9)
        self.client.post(
            reverse("admin:rulebook_team_change", args=[team.pk]),
            {"name": "New", "display_order": 10},
        )
        team.refresh_from_db()
        # Unticked rotates is saved as False.
        self.assertEqual((team.name, team.rotates, team.display_order), ("New", False, 10))

    def test_list_shows_teams(self):
        Team.objects.create(name="Listed team", rotates=False, display_order=9)
        response = self.client.get(reverse("admin:rulebook_team_changelist"))
        self.assertContains(response, "Listed team")

    def test_duplicate_name_is_refused(self):
        Team.objects.create(name="Test team", rotates=False, display_order=9)
        self.client.post(
            reverse("admin:rulebook_team_add"),
            {"name": "Test team", "display_order": 10},
        )
        self.assertEqual(Team.objects.filter(name="Test team").count(), 1)

    def test_anonymous_visitor_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("admin:rulebook_team_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])


class TeamSeedTests(TestCase):
    """RB-4: a data migration adds today's four teams."""

    def test_four_teams_are_seeded_in_order_with_rotation_flags(self):
        teams = Team.objects.values_list("name", "rotates", "display_order")
        self.assertEqual(
            list(teams),
            [
                ("Alpha", True, 1),
                ("Omega", True, 2),
                ("Wildcards", False, 3),
                ("New Members", False, 4),
            ],
        )


FRIDAY = 4


class RotationRuleTestCase(AdminTestCase):
    """RB-5: two rotating teams and one non-rotating team, apart from the seeded ones."""

    def setUp(self):
        super().setUp()
        self.red = Team.objects.create(name="Red", rotates=True, display_order=10)
        self.blue = Team.objects.create(name="Blue", rotates=True, display_order=11)
        self.green = Team.objects.create(name="Green", rotates=False, display_order=12)

    def rule(self, team=None, weekday=FRIDAY, nth=1, start=date(2026, 1, 1), until=None):
        return RotationRule.objects.create(
            weekday=weekday, nth=nth, team=team or self.red,
            effective_from=start, effective_until=until,
        )

    def post_rule(self, team, **overrides):
        data = {
            "weekday": FRIDAY, "nth": 1, "team": team.pk,
            "effective_from": "2026-01-01", "effective_until": "",
        }
        data.update(overrides)
        return self.client.post(reverse("admin:rulebook_rotationrule_add"), data)


class RotationRuleAdminTests(RotationRuleTestCase):
    """RB-5: Skye can add and edit rotation rules in the admin."""

    def test_add_a_rule_with_an_open_end(self):
        response = self.post_rule(self.red)
        self.assertRedirects(response, reverse("admin:rulebook_rotationrule_changelist"))
        rule = RotationRule.objects.get(team=self.red)
        self.assertEqual((rule.weekday, rule.nth, rule.effective_until), (FRIDAY, 1, None))

    def test_add_a_rule_with_an_inclusive_end_date(self):
        self.post_rule(self.red, effective_until="2026-06-30")
        self.assertEqual(
            RotationRule.objects.get(team=self.red).effective_until, date(2026, 6, 30)
        )

    def test_edit_a_rule(self):
        rule = self.rule()
        self.client.post(
            reverse("admin:rulebook_rotationrule_change", args=[rule.pk]),
            {"weekday": FRIDAY, "nth": 2, "team": self.blue.pk,
             "effective_from": "2026-01-01", "effective_until": ""},
        )
        rule.refresh_from_db()
        self.assertEqual((rule.nth, rule.team), (2, self.blue))

    def test_list_shows_rules(self):
        self.rule()
        response = self.client.get(reverse("admin:rulebook_rotationrule_changelist"))
        self.assertContains(response, "Red")

    def test_team_dropdown_offers_only_rotating_teams(self):
        response = self.client.get(reverse("admin:rulebook_rotationrule_add"))
        self.assertContains(response, "Red")
        self.assertNotContains(response, "Green")

    def test_a_non_rotating_team_is_refused(self):
        self.post_rule(self.green)
        self.assertFalse(RotationRule.objects.filter(team=self.green).exists())

    def test_the_model_refuses_a_non_rotating_team_too(self):
        rule = RotationRule(
            weekday=FRIDAY, nth=1, team=self.green, effective_from=date(2026, 1, 1)
        )
        with self.assertRaises(ValidationError):
            rule.full_clean()

    def test_nth_outside_1_to_5_is_refused(self):
        for nth in (0, 6):
            with self.subTest(nth=nth):
                self.post_rule(self.red, nth=nth)
                self.assertFalse(RotationRule.objects.filter(nth=nth).exists())

    def test_an_end_before_the_start_is_refused(self):
        self.post_rule(self.red, effective_until="2025-12-31")
        self.assertFalse(RotationRule.objects.filter(team=self.red).exists())

    def test_anonymous_visitor_is_sent_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("admin:rulebook_rotationrule_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_a_team_with_rules_cannot_be_deleted(self):
        self.rule()
        with self.assertRaises(ProtectedError):
            self.red.delete()


class RotationRuleOverlapTests(RotationRuleTestCase):
    """RB-7: two rules for one (weekday, nth) never cover the same day."""

    def assertRefused(self, **kwargs):
        rule = RotationRule(
            weekday=kwargs.get("weekday", FRIDAY), nth=kwargs.get("nth", 1),
            team=self.blue, effective_from=kwargs["start"],
            effective_until=kwargs.get("until"),
        )
        with self.assertRaises(ValidationError):
            rule.full_clean()

    def assertAllowed(self, **kwargs):
        RotationRule(
            weekday=kwargs.get("weekday", FRIDAY), nth=kwargs.get("nth", 1),
            team=self.blue, effective_from=kwargs["start"],
            effective_until=kwargs.get("until"),
        ).full_clean()

    def test_overlapping_ranges_are_refused(self):
        self.rule(start=date(2026, 1, 1), until=date(2026, 6, 30))
        self.assertRefused(start=date(2026, 6, 1), until=date(2026, 12, 31))

    def test_ranges_touching_on_one_day_are_refused(self):
        self.rule(start=date(2026, 1, 1), until=date(2026, 6, 30))
        self.assertRefused(start=date(2026, 6, 30))

    def test_the_day_after_the_old_rule_ends_is_allowed(self):
        self.rule(start=date(2026, 1, 1), until=date(2026, 6, 30))
        self.assertAllowed(start=date(2026, 7, 1))

    def test_an_open_ended_old_rule_blocks_any_later_start(self):
        self.rule(start=date(2026, 1, 1))
        self.assertRefused(start=date(2030, 1, 1))

    def test_a_new_open_ended_rule_that_starts_before_an_old_one_is_refused(self):
        self.rule(start=date(2026, 6, 1), until=date(2026, 6, 30))
        self.assertRefused(start=date(2026, 1, 1))

    def test_a_different_nth_or_weekday_is_allowed(self):
        self.rule(nth=1)
        self.assertAllowed(nth=2, start=date(2026, 1, 1))
        self.assertAllowed(weekday=3, start=date(2026, 1, 1))

    def test_editing_a_rule_does_not_clash_with_itself(self):
        rule = self.rule()
        rule.effective_until = date(2026, 12, 31)
        rule.full_clean()

    def test_the_admin_refuses_an_overlap(self):
        self.rule()
        self.post_rule(self.blue, effective_from="2026-03-01")
        self.assertEqual(RotationRule.objects.filter(team=self.blue).count(), 0)


class TeamOnTests(RotationRuleTestCase):
    """RB-5, RB-7: which team a date had, from the rules in force that day."""

    def test_a_rule_ended_and_replaced_applies_on_each_side_of_the_change(self):
        self.rule(team=self.red, start=date(2026, 1, 1), until=date(2026, 6, 30))
        self.rule(team=self.blue, start=date(2026, 7, 1))
        # 2026-06-05 and 2026-07-03 are both 1st Fridays.
        self.assertEqual(RotationRule.team_on(date(2026, 6, 5)), self.red)
        self.assertEqual(RotationRule.team_on(date(2026, 7, 3)), self.blue)

    def test_the_end_date_itself_still_has_the_old_team(self):
        # 2026-05-01 is a 1st Friday: end the old rule on it and start the new one next day.
        self.rule(team=self.red, start=date(2026, 1, 1), until=date(2026, 5, 1))
        self.rule(team=self.blue, start=date(2026, 5, 2))
        self.assertEqual(RotationRule.team_on(date(2026, 5, 1)), self.red)

    def test_a_date_before_every_rule_has_no_team(self):
        self.rule(start=date(2026, 1, 1))
        self.assertIsNone(RotationRule.team_on(date(2025, 12, 5)))

    def test_a_weekday_with_no_rule_has_no_team(self):
        self.rule(weekday=FRIDAY)
        # 2026-03-06 is a 1st Friday; 2026-03-05 is a Thursday.
        self.assertEqual(RotationRule.team_on(date(2026, 3, 6)), self.red)
        self.assertIsNone(RotationRule.team_on(date(2026, 3, 5)))


class RotationSeedTests(TestCase):
    """RB-5: a data migration adds today's rotation from 2025-08-01."""

    def test_sunday_alternates_alpha_and_omega_and_the_5th_has_none(self):
        expected = {
            date(2025, 8, 3): "Alpha", date(2025, 8, 10): "Omega",
            date(2025, 8, 17): "Alpha", date(2025, 8, 24): "Omega",
        }
        for day, name in expected.items():
            with self.subTest(day=day):
                self.assertEqual(RotationRule.team_on(day).name, name)
        self.assertIsNone(RotationRule.team_on(date(2025, 8, 31)))

    def test_wednesday_follows_the_same_pattern(self):
        self.assertEqual(RotationRule.team_on(date(2025, 8, 6)).name, "Alpha")
        self.assertEqual(RotationRule.team_on(date(2025, 8, 13)).name, "Omega")
        self.assertEqual(RotationRule.team_on(date(2025, 8, 20)).name, "Alpha")
        self.assertEqual(RotationRule.team_on(date(2025, 8, 27)).name, "Omega")

    def test_the_seed_has_eight_open_ended_rules(self):
        self.assertEqual(RotationRule.objects.count(), 8)
        self.assertFalse(RotationRule.objects.exclude(effective_until=None).exists())

    def test_a_date_before_the_seed_has_no_team(self):
        self.assertIsNone(RotationRule.team_on(date(2025, 7, 27)))
        self.assertIsNone(RotationRule.team_on(date(2025, 7, 30)))

    def test_a_future_first_sunday_is_alpha_and_a_5th_has_none(self):
        self.assertEqual(RotationRule.team_on(date(2026, 11, 1)).name, "Alpha")
        self.assertIsNone(RotationRule.team_on(date(2026, 11, 29)))

    def test_running_the_seed_again_adds_nothing(self):
        migration = importlib.import_module("rulebook.migrations.0006_seed_rotation")
        migration.seed(django_apps, None)
        self.assertEqual(RotationRule.objects.count(), 8)
        self.assertEqual(Team.objects.count(), 4)
