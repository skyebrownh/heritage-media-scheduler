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

Added by the first issue that adds code.

### Run

Added by the first issue that adds code.

### Test

```sh
uv run --env-file .env python manage.py test
```

## How work happens

Every change starts from a GitHub issue; [CLAUDE.md](CLAUDE.md) has the project's conventions.
