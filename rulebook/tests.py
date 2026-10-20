import importlib

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from rulebook.models import EventType, MediaRole, Position


class AdminTestCase(TestCase):
    """Logs in a fictional superuser, since the admin is the only interface."""

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
