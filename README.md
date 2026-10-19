# heritage-media-scheduler

Decides who serves in HICC's monthly media schedule, from Skye's rulebook, roster and the team's availability.

## What it does

Skye keeps the media team's rulebook (services, slot templates, team rotation, exceptions) and roster (qualifications, teams, personal limits) in one Django admin. For a new month she runs three steps: **generate** the month's events and empty slots, **fill** them, and **check** the result. She then reviews the schedule page and pastes its table into the month's Google Doc. The full spec is in [SPEC.md](SPEC.md).

## Getting started

### Prerequisites

- Python 3.13 and [uv](https://docs.astral.sh/uv/)
- Postgres 18, running locally
- The Railway CLI, for deploys and backups

### Install

```sh
uv sync                                  # install the pinned packages
cp .env.example .env                     # then put a real SECRET_KEY in .env (the file says how)
createdb heritage_media_scheduler        # the scheduler's own local database
uv run --env-file .env python manage.py migrate
uv run --env-file .env python manage.py createsuperuser
```

### Run

```sh
uv run --env-file .env python manage.py runserver
```

Then log in at <http://localhost:8000/admin/>.

## Deploy

Production is a Railway service in heritage-media-availability's project, with its own Postgres 18 service. Railway settings are set in the service's settings page (there is no `railway.toml`):

| Setting | Value |
| --- | --- |
| Build command | `python manage.py collectstatic --noinput` |
| Pre-deploy command | `python manage.py migrate` |
| Start command | `gunicorn config.wsgi --bind 0.0.0.0:$PORT` |
| Health check path | `/health/` |

Variables on the service:

| Variable | Value |
| --- | --- |
| `SECRET_KEY` | a new random key, never reused from local |
| `DEBUG` | `false` |
| `ALLOWED_HOSTS` | the service's Railway domain, plus `healthcheck.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://` plus the service's Railway domain |
| `DATABASE_URL` | a reference to the Postgres service's `DATABASE_URL` |

Create Skye's login once with `railway ssh` (a shell inside the running service, so it can reach the private database), then `python manage.py createsuperuser`. Don't use `railway run`: it runs on your Mac, where Railway's private database address doesn't resolve.

### Test

```sh
uv run --env-file .env python manage.py test
```

## How work happens

Every change starts from a GitHub issue; [CLAUDE.md](CLAUDE.md) has the project's conventions.
