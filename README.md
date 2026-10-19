# heritage-media-scheduler

Decides who serves in HICC's monthly media schedule, from Skye's rulebook, roster and the team's availability.

## What it does

Skye keeps the media team's rulebook (services, slot templates, team rotation, exceptions) and roster (qualifications, teams, personal limits) in one Django admin. For a new month she runs three steps: **generate** the month's events and empty slots, **fill** them, and **check** the result. She then reviews the schedule page and pastes its table into the month's Google Doc. The full spec is in [SPEC.md](SPEC.md).

## Getting started

### Prerequisites

- Python 3.13 and [uv](https://docs.astral.sh/uv/)
- Postgres 18, running locally. On macOS with Homebrew: `brew install postgresql@18` and `brew services start postgresql@18`. Homebrew doesn't put a versioned Postgres on your PATH, so add `export PATH="/opt/homebrew/opt/postgresql@18/bin:$PATH"` to `~/.zshrc` and open a new terminal tab
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

### Test

```sh
uv run --env-file .env python manage.py test
```

## Deploy

Production is a Railway service in heritage-media-availability's project, with its own Postgres 18 service. Merging to `main` deploys it, so **every merge goes live**. Railway's config-as-code files are being retired, so there is no `railway.json`: the settings below are entered in the service's Settings page, and they match heritage-media-availability's.

| Setting | Value |
| --- | --- |
| Builder | Railpack (installs exactly what's in `uv.lock`) |
| Pre-deploy command | `python manage.py migrate --noinput` |
| Start command | `python manage.py migrate --check && python manage.py collectstatic --noinput && gunicorn config.wsgi` |
| Health check path | `/health/` |

On each deploy, Railway builds, runs the pre-deploy migrate (if it fails, the previous version keeps running), then starts the app: `migrate --check` refuses to start if a migration is missing, `collectstatic` gathers the admin's styles for WhiteNoise, and gunicorn starts with the settings in `gunicorn.conf.py`. It waits for `/health/` to answer `ok` before switching over.

Variables on the service:

| Variable | Value |
| --- | --- |
| `SECRET_KEY` | a new random key, never reused from local |
| `DEBUG` | `false` |
| `ALLOWED_HOSTS` | the service's Railway domain, plus `healthcheck.railway.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://` plus the service's Railway domain |
| `DATABASE_URL` | a reference to the Postgres service's `DATABASE_URL` |

Create Skye's login once with `railway ssh` (a shell inside the running service, so it can reach the private database), then `python manage.py createsuperuser`. Don't use `railway run`: it runs on your Mac, where Railway's private database address doesn't resolve.

## How work happens

Every change starts from a GitHub issue; [CLAUDE.md](CLAUDE.md) has the project's conventions.
