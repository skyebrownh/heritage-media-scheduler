# heritage-media-scheduler: spec

2026-10-19 · Skye Brown

## Problem statement

Every month, Skye decides by hand who serves in each media position at Heritage International Christian Church (HICC). A month has about 15–25 services and events and about 16 volunteers, and each decision has to weigh who is unavailable, who is trained for which role, which team is on that week, each person's own limits (for example "Wednesdays and On Call only" or "3rd Sundays only"), how much each person can take on, and one-off exceptions like Thanksgiving week. Most of those rules live in her head. The result is typed into a Google Doc, the "HICC Media Serving Schedule", that the team reads.

This takes real time every month, it's easy to miss a conflict, and nothing checks the result. StewardHQ, the earlier attempt, stored schedules but never enforced a single rule, and its auto-scheduler was never started.

## Overview

**In one line:** Decides who serves in HICC's monthly media schedule, from Skye's rulebook, roster and the team's availability.

**Today:** Skye builds each month's schedule by hand in the last week of the previous month, from the availability responses and what she remembers about each person, then types it into the month's Google Doc.

**Goal:** Skye keeps her rulebook and roster in one admin. For a new month she runs three steps: **generate** the month's events and empty slots, **fill** them, and **check** the result. She reviews the schedule page, adjusts anything in the admin, and pastes the table into the month's Doc. Along the way, the scheduler shows which choices its rules couldn't decide, so the rules she still applies by feel can be written down.

**Success for v1:** A month's published schedule was drafted by `fill`, passed `check` with no hard failures, and needed only small edits from Skye.

## Users and roles

| Role | Who | How they get in | What they can do |
| --- | --- | --- | --- |
| Admin | Skye, the media schedule coordinator (one person, comfortable with tech) | Django admin login (username and password) on the hosted app | Everything: edit the rulebook and roster, enter special events, run the steps, review and edit schedules, import history |

Volunteers never use this app. They see the schedule only in the Google Doc that Skye publishes.

## Scope

### In v1

- A thin slice: a Django project deployed on Railway, with its own Postgres, the Unfold admin and Skye's login.
- The rulebook in the admin, with effective dates: recurring services, slot templates, teams, the team rotation, positions and dated exceptions.
- The roster in the admin: qualifications, team membership, person rules and the workload lean, keyed by `member_id`.
- Special events entered in the admin, with the positions each one needs.
- `generate`: a month's events and empty slots from the rulebook, exceptions and special events.
- History import: Skye's Docs from Aug 2025 to Oct 2026 loaded as published schedules, with name matches she confirms.
- `check`, with the `check_history` report over every imported month.
- `fill`, with a per-slot record of who was eligible, which rule decided and where ties remained.
- The schedule page: the Doc-shaped table, counts by team, the Unavailable list, warnings and the tie report, behind the login.
- `fetch_availability`: loading a month's availability from heritage-media-availability's endpoint, once that endpoint exists.

### Later

- Admin buttons that run `generate`, `fill` and `check`, in addition to the management commands.
- A repair step in `fill` that swaps people to fill a slot the first pass left empty, if dead ends show up in practice.
- `fill` suggesting training opportunities for people in training.
- Importing special events from the media requests module's endpoint, once it exists.
- A read-only JSON view of a schedule, if the deferred Schedule UI needs one.

### Non-goals

- **Pages for volunteers.** The admin, behind Skye's login, is the only interface. Volunteers see the Google Doc.
- **A schedule-editing UI beyond the admin.** The Schedule UI that replaces the Doc is a separate, deferred project.
- **Collecting availability or requests.** heritage-media-availability and the media requests process own those. The scheduler only reads them.
- **Google integration.** Skye copies the schedule page into the Doc herself, and downloads past Docs by hand for import.
- **Notifications.** Nobody is emailed or messaged.
- **Anything generic or multi-ministry.** It's built for HICC media, with HICC names. StewardHQ's generic "platform" design is what stalled it.

## Functional requirements

### Rulebook (RB)

| ID | Requirement |
| --- | --- |
| RB-1 | Skye can add, edit and end recurring services in the admin: event type, weekday, start and end time, title, and effective dates. |
| RB-2 | Each recurring service has a slot template: the positions it needs, each marked required, preferred, optional or not needed, with effective dates per line. |
| RB-3 | Skye can define positions. A position covers one media role, or two roles shared by one person (Sound + ProPresenter). Each media role has a column in the schedule table, so a shared position shows its person in each of its roles' columns. |
| RB-4 | Skye can define teams and mark which ones rotate. Today that's Alpha and Omega (rotating), and Wildcards and New Members (not rotating). |
| RB-5 | Skye can set the team rotation as (weekday, nth) → team, with effective dates. Today: Alpha on the 1st and 3rd Sunday and Wednesday, Omega on the 2nd and 4th. A 5th weekday has no team. |
| RB-6 | Skye can add dated exceptions: cancel a recurring service on a date, or change its times or title on a date, with a note. |
| RB-7 | Every rule answers "what applied on this date?" from its effective dates, so a past month is judged by the rules in force at the time. |

### Roster (RS)

| ID | Requirement |
| --- | --- |
| RS-1 | Skye can record each member's level per media role (not trained, in training or qualified), with a "since" date. Members are identified by `member_id` from heritage-media-availability. |
| RS-2 | Skye can record team membership with effective dates. A member is on at most one team at a time. |
| RS-3 | Skye can give a member person rules: allowed weekdays, allowed event types, allowed roles, and set patterns as (nth, weekday) pairs, such as "3rd Sunday". An empty rule means no restriction. The rules combine with AND: a slot is allowed only when it passes every non-empty rule. |
| RS-4 | Skye can set each member's workload lean: lighter, normal or more. |
| RS-5 | The admin shows members by name, read from the newest availability snapshot, never from a copy the scheduler edits. |

### Special events (SE)

| ID | Requirement |
| --- | --- |
| SE-1 | Skye can enter a special event: date, start and end time, event type, title and notes, plus the positions it needs, each with a level. |

### Generate (GN)

| ID | Requirement |
| --- | --- |
| GN-1 | `generate <YYYY-MM>` creates the month's schedule: one event for each recurring service that applies on each date, after exceptions, plus each special event in the month, each with empty slots from its template or its own position list. |
| GN-2 | Each Sunday and Wednesday event is labelled with that week's team from the rotation. 5th-week events have no team. |
| GN-3 | `generate` refuses to run if the month already has a schedule, so it never overwrites Skye's work. |
| GN-4 | `generate <YYYY-MM> --compare` builds an imported month in memory and compares it with the imported schedule: the same dates, event types and positions. Any difference is reported, not hidden. It never saves, so GN-3 still holds. |

### Check (CK)

| ID | Requirement |
| --- | --- |
| CK-1 | `check` reports a **hard failure** for any slot whose person is inactive, isn't qualified for every role the position covers, or is unavailable that day. Inactive is judged only for draft schedules: `check_history` skips it, because the endpoint knows only who is active today. |
| CK-2 | `check` reports a **warning** when one person holds two positions in one event (On Call included), or is placed against their own person rules. |
| CK-3 | A trainee can be added to a slot as a **shadow** (an extra name beside the qualified person) or as **serving with help** (filling the position, with a named helper qualified in that role). `check` shows trainees as notes, and warns when the helper holds another position in that event. |
| CK-4 | `check` lists everyone with no availability response for the month as a warning. They count as available. |
| CK-5 | `check` lists required and preferred slots left empty. |
| CK-6 | `check_history` runs `check` over every imported month and reports roster findings ("not qualified", "not on that team") separately from rule findings. |

### Fill (FL)

| ID | Requirement |
| --- | --- |
| FL-1 | `fill <YYYY-MM>` fills only empty slots. Slots Skye has placed or edited are never changed. |
| FL-2 | `fill` never assigns anyone in breach of a hard rule (CK-1) or their person rules (RS-3), never assigns a trainee, and never puts one person in two positions in one event. A slot it can't fill stays empty, with a warning. |
| FL-3 | `fill` works through slots in level order (required, then preferred, then optional), and within a level starts with the slot that has the fewest eligible people. |
| FL-4 | Among eligible people, `fill` prefers, in order: members of that week's team; the person with the fewest qualifications; the person whose workload lean and serves so far this month leave them most room; then the lowest `member_id`, as a fixed tie-break. |
| FL-5 | `fill` is deterministic: the same inputs always give the same schedule. |
| FL-6 | For every slot it fills, `fill` records who was eligible, which preference decided, and whether it came down to the tie-break. |

### Schedule page (PG)

| ID | Requirement |
| --- | --- |
| PG-1 | Behind the login, a page shows a month's schedule as a table shaped like the Doc's: Date, ProPresenter, Sound, the camera columns (Director, Main 1, Main 2, Mobile 3), On Call, Unavailable and Notes. "Not needed" cells are blank. |
| PG-2 | Selecting the table in a browser and pasting it into Google Docs gives a real table. |
| PG-3 | Below the table, the page shows each person's serve count (every event except On Call), On Call count and total, grouped by team. |
| PG-4 | The page shows the Unavailable list by person, non-responders, `check`'s findings, and `fill`'s tie report. |

### History (HI)

| ID | Requirement |
| --- | --- |
| HI-1 | `import_doc` reads a Doc downloaded as a web page and loads it as that month's published schedule: events, positions and assignments, the Unavailable column as that month's availability, and team membership from the team-count section. |
| HI-2 | The importer proposes matches from names in the Doc to members in the newest endpoint snapshot, and Skye confirms them in the admin. A month with an unconfirmed name doesn't load. |
| HI-3 | A struck-out name means not assigned. Text in brackets or in Notes is kept as a note, not as an assignment. |
| HI-4 | Importing a month that already has a schedule replaces it only when Skye asks, so a final Doc can be brought back after edits. |

### Availability input (AV)

| ID | Requirement |
| --- | --- |
| AV-1 | `fetch_availability <YYYY-MM>` calls heritage-media-availability's endpoint with a token and stores the response as that month's snapshot, including member names and active status. |
| AV-2 | No submission for a month means "didn't respond", which is different from "available all month". |

## Key user flows

### Building next month's schedule

1. In the last week of the month, Skye enters any special events for next month in the admin, and adds any exceptions.
2. She runs `fetch_availability` for next month, then `generate`.
3. Optionally, she places some people herself, such as a trainee serving with help.
4. She runs `fill`, then `check`.
5. On the schedule page she reads the warnings and the tie report, and edits slots in the admin, re-running `fill` or `check` as needed.
6. She selects the table, pastes it into the month's Doc, publishes the Doc as usual, and marks the schedule published in the admin.
7. If she edits the Doc later, she can re-import it with `import_doc`.

### Loading history

1. Skye downloads a month's Doc as a web page.
2. She runs `import_doc` with that file.
3. In the admin she confirms the name matches it proposes, adding any former volunteer to heritage-media-availability as an inactive member first.
4. She runs `import_doc` again, and the month loads. The downloaded file can then be deleted.
5. Once months are loaded, she runs `check_history` and reads the report to find gaps in the rulebook and roster.

### Changing a rule

1. Skye ends the old rule (sets its "until" date) and adds the new one from its start date, for example Wednesday's template without Main 2 from Sep 2026.
2. Past months keep being judged by the old rule, and new months use the new one.

## Business rules

- **People are identified only by `member_id`.** Nothing matches people by name automatically. Names come only from stored availability snapshots, and the history importer's name matches need Skye's confirmation.
- **Days are America/New_York calendar dates.** Availability is by whole day. Times are stored as local times on a date, so an evening service never moves to another day.
- **One schedule per month,** and one slot per position per event.
- **The hard rules are only: active, qualified, available.** Everything else is a warning or a preference.
- **Team weeks are a preference, never a failure.**
- **Only qualified members fill slots.** People in training are added only by Skye, as a shadow or serving with help.
- **Fairness is measured within one month only,** and is shaped by each person's lean, not spread evenly.
- **`fill` never changes a slot Skye placed or edited.**
- **Rules are never edited in place for past dates.** A change ends the old rule and adds a new one, so history stays judged by its own rules.
- **The scheduler never writes to heritage-media-availability,** and never reads its database directly. It reads only the endpoint.

## Data model

All tables live in the scheduler's own Postgres. `member_id` is heritage-media-availability's integer member id. There is no foreign key across projects.

### team

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| name | text | Unique, e.g. Alpha, Omega, Wildcards, New Members |
| rotates | boolean | True for teams that take turns by week |
| display_order | integer | Order in the counts section |

### media_role

| Field | Type | Notes |
| --- | --- | --- |
| code | text | Primary key, e.g. `propresenter`, `sound`, `camera_director`, `main_camera_1`, `main_camera_2`, `mobile_camera_3`, `on_call` |
| name | text | |
| is_active | boolean | |
| column | text | The schedule table column it appears in |
| display_order | integer | Column order in the schedule table |

### position

| Field | Type | Notes |
| --- | --- | --- |
| code | text | Primary key, e.g. `sound`, `sound_propresenter` |
| name | text | |
| roles | many-to-many → media_role | One role, or two for a shared position |

### event_type

| Field | Type | Notes |
| --- | --- | --- |
| code | text | Primary key: `service`, `prayer`, `special_event` |
| name | text | |

### recurring_service

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| event_type | → event_type | |
| weekday | integer | 0 = Monday … 6 = Sunday |
| title | text | |
| starts_at, ends_at | time | Local time. `starts_at < ends_at` |
| effective_from | date | Required |
| effective_until | date | Optional, inclusive |

### slot_template_line

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| recurring_service | → recurring_service | |
| position | → position | |
| level | text | `required`, `preferred`, `optional`, `not_needed` |
| effective_from, effective_until | date | As above |

### rotation_rule

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| weekday | integer | |
| nth | integer | 1–5 |
| team | → team | |
| effective_from, effective_until | date | |

### service_exception

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| date | date | |
| recurring_service | → recurring_service | |
| action | text | `cancel` or `change` |
| starts_at, ends_at, title | time, time, text | Optional overrides for `change` |
| note | text | Shown in the schedule's Notes |

### special_event and special_event_line

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| date | date | |
| starts_at, ends_at | time | |
| event_type | → event_type | |
| title, notes | text | |
| lines | special_event_line (position, level) | The positions this event needs |

### qualification

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| member_id | integer | |
| media_role | → media_role | Unique with member_id |
| level | text | `not_trained`, `in_training`, `qualified` |
| since | date | Optional, approximate is fine |

### team_membership

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| member_id | integer | |
| team | → team | |
| effective_from, effective_until | date | Periods for one member never overlap |

### member_profile

| Field | Type | Notes |
| --- | --- | --- |
| member_id | integer | Primary key |
| lean | text | `lighter`, `normal`, `more` |
| allowed_weekdays | list of integers | Empty = any |
| allowed_event_types | many-to-many → event_type | Empty = any |
| allowed_roles | many-to-many → media_role | Empty = any qualified role |
| patterns | list of (nth, weekday) | Empty = no fixed pattern |

### availability_snapshot

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| month | text | `YYYY-MM` |
| source | text | `endpoint` or `doc_import` |
| fetched_at | timestamp | The newest snapshot per month counts |
| payload | JSON | The endpoint's shape: members (id, names, active, standing availability) and current submissions |

### name_alias

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| doc_name | text | Unique, as written in the Docs |
| member_id | integer | Optional until confirmed |
| confirmed | boolean | |

### schedule

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| month | text | `YYYY-MM`, unique |
| status | text | `draft` or `published`. Skye marks a schedule published in the admin after pasting it into the Doc. `import_doc` loads a month as published. |
| source | text | `generated` or `imported` |

### event

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| schedule | → schedule | |
| date | date | |
| starts_at, ends_at | time | |
| event_type | → event_type | |
| title, notes | text | |
| team | → team | Optional: none on 5th weeks, Saturdays and most special events |

### slot

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| event | → event | |
| position | → position | Unique with event |
| level | text | As in templates |
| member_id | integer | Optional: empty until filled |
| placed_by | text | `skye`, `fill` or `import` |
| trainee_member_id | integer | Optional |
| trainee_kind | text | `shadow` or `with_help` |
| helper_member_id | integer | Required when `trainee_kind` is `with_help` |
| note | text | |

### fill_record

| Field | Type | Notes |
| --- | --- | --- |
| id | integer | Primary key |
| slot | → slot | |
| eligible | JSON | `member_id`s after the hard rules and person rules |
| deciding_rule | text | `only_choice`, `team`, `flexibility`, `workload` or `tie_break` |
| filled_at | timestamp | |

The model leaves room for: more roles and positions, more teams, more event types, and a later read-only JSON view of a schedule.

## Non-functional requirements

- **Security.** Only Skye's admin login reaches any page. Secrets (Django's secret key, the database URL, the availability token) come from environment variables, with a `.env.example` of placeholders. `DEBUG` is off in production, and Django's deploy check passes.
- **Privacy.** The repo is private. No real names or `member_id`-linked data are ever committed: tests use fictional people, and real data lives only in the hosted database and Skye's local copies.
- **Cost.** About $5–6 a month extra on Railway's Hobby plan, for one small service and one small Postgres.
- **Backups.** Weekly, on Skye's Mac: a scheduled `pg_dump` of production's Postgres through the Railway CLI, the same approach heritage-media-availability uses. Backups stay on the Mac.
- **Speed.** `generate`, `check` and `fill` each finish within a few seconds for a month.
- **Devices.** The admin and schedule page are used on a laptop. They should work on a phone, but aren't designed for one.
- **Time.** Every date is an America/New_York date, and tests cover the Wednesday 6:30–8:00 pm service, which crosses UTC midnight.

## Technical approach

| Layer | Choice | Why |
| --- | --- | --- |
| Language | Python 3.13, managed with uv | Matches heritage-media-availability and Skye's preference |
| Framework | Django | The admin edits every table with little code, and its login protects the schedule page. Skye already knows it from availability. |
| Admin look | django-unfold, version pinned | The same look and components as availability's admin |
| Database | Postgres 18, the scheduler's own | Matches availability locally and in production, so backups and snapshot loading work the same way |
| Hosting | Railway, in heritage-media-availability's Railway project, production only, as its own service with its own Postgres | Everything in one place. The same project allows private networking to availability's endpoint. No per-project fee. |
| Serving | gunicorn, with WhiteNoise for static files | Same as availability |
| Fill algorithm | A hand-written, deterministic greedy picker | Its per-slot decisions can be explained and recorded, which is how the tie report works. No dependency. |

**Modules:**

- **Engine:** plain Python, with no Django or database. It holds the eligibility filter, `generate`, `check` and `fill`. Its inputs are plain values (the rules in force, the roster, availability, a schedule), and its outputs are a schedule, findings and fill records.
- **Rulebook and roster:** the Django models and admin for every table above. They turn database rows into the engine's inputs.
- **Commands:** `generate`, `fill`, `check`, `check_history`, `import_doc` and `fetch_availability`. Each loads data, calls the engine and saves the result.
- **History import:** reads a downloaded Doc into the same schedule and snapshot shapes the engine uses.
- **Availability client:** calls the endpoint with the token and stores the snapshot.
- **Schedule page:** an Unfold admin page that renders a schedule, its counts, findings and fill records.

**Alternatives:**

- The scheduler as an app inside availability's Django project, sharing its database. It would cost about $5 a month less, but it recreates StewardHQ's coupling: one database, and every scheduler deploy putting the live availability form at risk.
- A constraint solver (OR-Tools) for `fill`. It avoids dead ends and balances globally, but it can't say why it chose someone, and it adds a large dependency.
- SQLite on a Railway volume. It's about $3 a month cheaper, but it differs from availability's setup and backups.

## Testing approach

- **Good tests:** test behaviour through public paths. The engine is tested with Django's `SimpleTestCase`, which refuses any database query, by passing plain inputs and checking outputs. Models, admin, commands and pages are tested with `TestCase` against a throwaway test database, as in heritage-media-availability.
- **What gets tested:** every requirement ID except PG-2, which is checked by hand, has at least one test, and test docstrings cite the ID. Every hard rule, warning and fill preference has a test that isolates it. That includes a test that each preference decides when the earlier ones tie, a determinism test (running `fill` twice gives the same result), and a test for the Wednesday evening service across UTC midnight.
- **Test data:** fictional people only, in availability's style (Bob Smith, Bob Jones, Jane Doe, and so on), each chosen to cover a case.
- **Not tested automatically:** the schedule page's look, and pasting it into Google Docs (checked by hand); and how well the rules match Skye's real decisions. That's the job of `check_history`, a report run against real data in the database, not a test.
- **Command:** `uv run --env-file .env python manage.py test`, run locally before every push or merge. There's no CI.
- **Examples to follow:** filled in once the first tests exist.

## Timeline and open questions

| Milestone | Dates | Focus |
| --- | --- | --- |
| Thin slice | — | Django project deployed on Railway with its own Postgres, the Unfold admin and Skye's login |
| Rulebook and roster | — | Every rulebook and roster table in the admin, with effective dates |
| Generate | — | `generate`, checked against imported months' rows |
| Live availability | — | `fetch_availability`, once availability's endpoint exists |
| History and check | — | `import_doc`, name matching, `check`, `check_history` and the schedule page |
| Fill | — | `fill` with its fill records and tie report |

### Open questions

- How Railway environments behave when the scheduler's services are added to availability's project, which has production and staging: whether the scheduler can exist in production only. This is settled in the thin slice. If it can't, the scheduler gets its own Railway project and calls the endpoint over its public URL.
- The availability endpoint's exact shape and token handling belong to an issue in heritage-media-availability, after its Oct 25 launch.
- How FL-4 turns workload lean and serves so far into "most room". Settled when Fill is planned, using what `check_history` shows.
- Whether a Doc downloaded as a web page keeps strikethrough, brackets and the team-count section in a form the importer can read (HI-1, HI-3). Settled by inspecting one real export at the start of the History issue.

## Decisions

- 2026-10-19: The scheduler is hosted on Railway with a Django admin and its own database, replacing architecture.md's "runs on Skye's machine, no hosting, JSON and HTML files" plan. Everything the scheduler owns, including the rulebook, lives in the database and is edited in the admin, so changing a rule never means editing a file. architecture.md is updated to match.
- 2026-10-19: Rules, templates, rotation and team membership carry effective dates, so `check_history` judges each past month by its own rules. The first known changes are Saturday prayer from Aug 2025 and Wednesday without Main 2 from Sep 2026.
- 2026-10-19: History comes from Skye's Docs from Aug 2025 to Oct 2026, the months with one stable layout. Earlier Docs and StewardHQ's database aren't imported.
- 2026-10-19: The build order is generate, then live availability, then history and check, then fill. History needs availability's member list to match names against. `check` comes before `fill`, so `check_history` can find gaps in the rules before anything is filled automatically.
- 2026-10-19: Testing against real months is a report (`check_history`), not part of the test suite, so the suite only ever needs fictional data.
- 2026-10-19: There's one production environment, with local runs for testing and no staging, because Skye is the only user.
