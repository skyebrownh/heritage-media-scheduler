from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from rulebook.models import EventType, MediaRole


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
