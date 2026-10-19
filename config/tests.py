from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings

from config.settings import parse_database_url


class ParseDatabaseUrlTests(SimpleTestCase):
    """Thin slice: settings read the database from DATABASE_URL."""

    def test_parses_url_into_django_database_settings(self):
        db = parse_database_url("postgres://bob:s3cret@db.example.com:5433/sched")
        self.assertEqual(
            db,
            {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": "sched",
                "USER": "bob",
                "PASSWORD": "s3cret",
                "HOST": "db.example.com",
                "PORT": 5433,
            },
        )

    def test_missing_url_raises_clear_error(self):
        with self.assertRaisesMessage(ValueError, "DATABASE_URL"):
            parse_database_url("")

    def test_malformed_url_raises_clear_error(self):
        with self.assertRaisesMessage(ValueError, "DATABASE_URL"):
            parse_database_url("not-a-url")


class HealthTests(SimpleTestCase):
    """Thin slice: /health/ is the one open page, and it shows no data."""

    def test_health_answers_ok_without_login(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_health_is_not_redirected_to_https(self):
        # Railway's health check calls over plain HTTP.
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)


class LoginRequiredTests(SimpleTestCase):
    """Thin slice: anyone not logged in is sent to the login page."""

    def test_anonymous_admin_visit_goes_to_login(self):
        response = self.client.get("/admin/")
        self.assertRedirects(
            response, "/admin/login/?next=/admin/", fetch_redirect_response=False
        )

    def test_root_redirects_to_admin(self):
        response = self.client.get("/")
        self.assertRedirects(response, "/admin/", fetch_redirect_response=False)


class AdminTests(TestCase):
    """Thin slice: Skye's login reaches the Unfold admin."""

    def test_logged_in_superuser_reaches_admin(self):
        User.objects.create_superuser("jane-doe", password="test-only-pw")
        self.client.login(username="jane-doe", password="test-only-pw")
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)

    def test_unfold_comes_before_django_admin(self):
        apps = settings.INSTALLED_APPS
        self.assertLess(apps.index("unfold"), apps.index("django.contrib.admin"))
