# CLAUDE.md

## heritage-media-scheduler

Decides who serves in HICC's monthly media schedule, from Skye's rulebook, roster and the team's availability. It's for Skye, the media schedule coordinator, who is its only user. **SPEC.md is the source of truth** for what it does and why. **GitHub issues** hold the work.

@SPEC.md

## Stack (do not change without asking)

- Python 3.13, managed with uv
- Django, with the Django admin as the only interface
- django-unfold for the admin, version pinned
- Postgres 18, the scheduler's own database (never availability's)
- Railway, inside heritage-media-availability's Railway project, production only, as its own service
- gunicorn, with WhiteNoise for static files
- Django's test runner: `SimpleTestCase` for the engine, `TestCase` for everything that touches the database
- Approved packages: django, django-unfold, psycopg, gunicorn, whitenoise. Anything else needs approval first. Parsing Docs and calling the availability endpoint use the standard library.

## Architecture

- `config/` is the Django project package (settings, URLs, WSGI). There is no Django app yet; later issues add them.
- `config/settings.py` is the only settings module. Everything comes from environment variables (see `.env.example`), and `DEBUG=false` switches on the production security settings.
- `/health/` (`config/views.py`) is the only page without a login. It touches no database and returns plain `ok`.
- `/` redirects to `/admin/`, the only interface.
- `gunicorn.conf.py` holds the production web server settings, so Railway's start command stays `gunicorn config.wsgi`. The Railway commands live in the service settings (README's Deploy section), not in a file.
- Static files are served by WhiteNoise; `collectstatic` writes them to the git-ignored `staticfiles/`.

## Conventions

- Code comments cite the requirement ID they implement (e.g. `# FL-4: <why>`), and test docstrings cite the IDs they cover.
- The engine (eligibility, `generate`, `check`, `fill`) is plain Python: no Django imports and no database. It takes plain values and returns plain values, and its tests use `SimpleTestCase`.
- People are identified only by `member_id`. Never match people by name in code, and never store names: they come from the newest availability snapshot.
- Rules are never edited in place for past dates. Every rule, template, rotation and team membership has effective dates, and a lookup asks "what applied on this date?"
- Dates are America/New_York calendar dates. Times are local times on a date, never converted through UTC.
- The scheduler never writes to heritage-media-availability and never reads its database. It reads only the endpoint.
- No real names or real `member_id`-linked data in the repo. Tests use fictional people (Bob Smith, Bob Jones, Jane Doe, …).
- Secrets come from environment variables. `.env` is git-ignored, and `.env.example` holds placeholders only.
- HICC-specific names (`MediaRole`, `rotation_rule`), not generic ones. Generalize only after needing the same thing three times.

## Commands

- Run locally: `uv run --env-file .env python manage.py runserver` (setup in README.md)
- Run tests: `uv run --env-file .env python manage.py test`

Project facts for Skye's personal skills (checks, merge style, whether merging deploys) are in `.claude/workflow.md`; update it with `/setup-project`.
