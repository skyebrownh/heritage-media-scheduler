# StewardHQ audit (October 2026)

This audit covers [stewardhq-api](https://github.com/skyebrownh/stewardhq-api) and [stewardhq-web](https://github.com/skyebrownh/stewardhq-web). It feeds the fresh start: `heritage-media-scheduler` (this folder) and `heritage-media-availability` (a separate repo).

Two agents wrote it by reading the code, the full git history, and every issue and PR. Nothing was run, and nothing on GitHub was changed. Items marked *(inferred)* came from reading the code and were not checked against the live deployment.

---

## 1. Urgent: security and privacy

Do these before any new work. They concern volunteers' data, not just code quality.

| # | Problem | Where | Fix |
|---|---|---|---|
| 1 | **Real volunteers' names, phone numbers and some emails are committed to a public repo.** About 16 people. The CSVs link first names to about a year of assignment and unavailability history. | API `app/db/scripts/seed.py:73-91`, `app/db/csv/*.csv`, in history since `0d9e128` (2025-12-20) | Make the repo private now. Scrub the history later (for example with `git-filter-repo`) if it must go public again. Deleting the files alone doesn't remove them from history. |
| 2 | **The API key is public.** The web app ships it as `VITE_STEWARDHQ_API_KEY`, and anything prefixed `VITE_` is built into the browser bundle. On API `main`, that key is the only protection for reads **and writes/deletes**. | web `src/api/client.ts:2,9`; API `app/main.py:47` | If the Railway API is still live, take it down or rotate the key. Production probably runs `main` *(inferred)*. |
| 3 | **Secrets are written to the logs at startup.** The whole settings object is logged, including the API key and `DATABASE_URL` with its password. | API `app/main.py:30` | Rotate the DB password if the logs were ever shared. Don't carry this pattern over. |
| 4 | Full tracebacks are returned whenever `ENV != "production"`, so `ENV=prod` would leak them. | API `app/utils/exception_handlers.py:101-108` | Leave behind. |

No credentials were found committed in either repo's history, and `.env` was git-ignored in both.

---

## 2. Intent vs. what it became

**Intent.** The API began on 2025-06-16 as the "HICC Media API": tables for media roles, one schedule per month, slots per role per date, and user availability by date. The web milestone "v1 MVP" said: *a one-page schedule grid that fully replaces the current Google Doc workflow.*

**What it became.** In January 2026 it was rebranded "StewardHQ", described as "a people-centric platform for managing team scheduling, availability, assignments, and training". Issue `#27` made generality an explicit goal. The API grew to 11 resource areas and about 45 endpoints:

- users
- teams and team membership
- roles, proficiency levels and user roles
- event types
- schedules and events
- assignments
- unavailable periods
- a grid view
- auth, CORS and environments

Planned on top: Redis, rate limiting, workers, pagination and performance testing.

**Where the creep actually was:**

- **In the API, not the web.** The web app stayed tightly on its one screen, the monthly grid. It calls 5 of the roughly 45 API routes.
- **Rewrites before anyone used it.** The API was built for 7 months before any screen existed. It went through three data-layer rewrites (Supabase → asyncpg raw SQL → SQLModel) and two full rewrites of the tests. Roughly 80% of API commits were plumbing.
- **Generic names, media-specific behaviour.** There was no tenant or ministry concept, and every event automatically got a slot for every role. So it paid the cost of being generic without the benefit.
- **Auth came before the MVP was finished.** Clerk sign-in came before availability entry (`web#3`) and event editing (`web#5`). It then needed 4 PRs of CORS fixes and was never merged to `main`.
- **The real goal was never started.** The auto-scheduler (`api#32`) has been the stated goal since day one, and it has no code.

### Timeline

| When | What happened |
|---|---|
| Jun 2025 | API phase 1: generic CRUD on Supabase. Infra issues opened (Redis, rate limiting, workers) before any schedule existed. |
| Jun–Nov 2025 | 5-month pause. The Supabase free database was shut down (`api#22`). |
| Dec 2025 | Rewrite 1 (Railway + raw SQL), test rewrite 1, then rewrite 2 (schema made generic, SQLModel, Alembic). |
| Jan 5, 2026 | First endpoint shaped for a screen (`GET /schedules/{id}/grid`), about 6.5 months in. Scheduling engine issue `#32` opened. |
| Jan 14 | Rebranded to StewardHQ; "training" added to the scope. |
| Jan 23–26 | Web app started. A polished read-only grid was deployed to production by day 4 (`95bcad7`). **The best stretch of focus.** |
| Jan 26–29 | Six restructure commits, a "major refactor before API write calls", a router mode switch, then Clerk. |
| Feb 4–5 | First write in the UI (change an assignment). Merged to `staging` only. Work stopped. The MVP milestone (due Feb 7) was missed. |

---

## 3. What went well (keep these habits)

- **The grid design is proven.** Events are rows, roles are columns, and a red "Unavailable" column sits at the end, matching the Google Doc the team already knows. Empty cells show a plus icon, and cells that don't apply show "—".
- **A clean schema with real constraints:**
  - one slot per (event, role), one row per (user, role) and per (team, user)
  - `CHECK starts_at < ends_at`
  - stable `code` keys on lookup tables
  - soft deletes, and 409 instead of a cascade when deleting history
- **Correct time-overlap logic** using half-open intervals: `a.start < b.end && a.end > b.start`.
- **One request fills the whole screen** (`GET /schedules/{id}/grid`), with no N+1 queries.
- **Serious API tests.** About 120, against real Postgres, with migrations run into a throwaway schema, fixed-UUID fixtures, parametrized error cases and fictional test people.
- **Careful web touches:**
  - After a save, the one changed cell is patched into the cache instead of reloading the whole grid.
  - The assignment editor opens as its own route, so each cell has a URL.
  - Loading, error and empty states everywhere.
  - Strict TypeScript.
  - A sensible default month.
- **Decisions were written down,** though in issue comments (`api#13`, `#14`, `#27`, `#35`), which is the wrong place.
- **The real scheduling rulebook exists as code** in `seed.py:128-249`:
  - service times
  - the Saturday prayer meeting
  - the team rotation (Alpha in weeks 1 and 3, Omega in weeks 2 and 4, no team in 5th weeks)
  - special events and holiday notes from CSVs
  - a Thanksgiving-week exception

---

## 4. What went poorly

**Scope and process**

- There was no scope document and no list of non-goals, so "platform" language crept in without anything to push back on it.
- The API was designed table-first (CRUD for every table) instead of screen-first. Gaps appeared the moment a UI existed (`api#40`, `#42`, `#43`).
- Production fell behind real work. `main` and `staging` drifted apart on both repos, and issues stayed open after their PRs merged.
- No CI on either repo, and no tests at all on the web.

**Domain logic gaps (the parts that matter for a scheduler)**

- **No assignment rules are enforced.** You can assign anyone to any slot: inactive, untrained, unavailable or double-booked. The data could express all of these checks, but no code uses them.
- **Slots don't depend on event type.** Every event gets every active role, so a prayer meeting gets camera slots.
- **Every user is given a row for every role,** so "no row" can't mean "not trained for that role".
- **Rules were lost in migrations:**
  - the `sound_only` and `sound_and_propresenter` CSV columns are ignored (they look like "one person covers both roles")
  - unique month schedules
  - unique unavailability per person and date
  - required (NOT NULL) timestamps
- **Timezone bug** *(inferred)*:
  - Month bounds are computed in UTC, and seeded unavailability is stored as UTC midnight.
  - Wednesday's 18:30–20:30 Eastern service crosses UTC midnight.
  - So a Thursday-only conflict can falsely overlap Wednesday's service.

**Web specifics**

- Saving gives no feedback: the modal closes before the save finishes, so failures are silent.
- "Can edit" is decided by sign-in alone, not the admin role.
- The person picker lists every user, not the people qualified for the role.
- You can't clear an assignment.
- Team names and role short names are hardcoded in components.
- Not usable on phones.
- The whole paid Catalyst UI kit was copied into a public repo, with 12 of its 27 components unused. Check its license.
- API types were copied by hand and have already drifted (nullable fields typed as always present). About 13 API functions are unused.

---

## 5. How the two repos worked together

- **The contract** was one screen-shaped read (`GET /schedules/{id}/grid`) plus `PATCH /assignments/{id}`. That was good. Everything else on the API went unused.
- **Types were copied by hand** from the Python models into TypeScript, including about 40 flattened join fields for a single assignment. Nothing was generated from FastAPI's OpenAPI spec.
- **Auth landed on both sides on the same day** (Feb 5), with CORS fixes piled on top. Web `staging` only works with API `staging`.
- **Naming confusion:** the routes say "availability", but the data is *un*availability. The grid's `availability` field lists the people who *can't* serve.

---

## 6. Availability: the input contract

**How StewardHQ handled it:**

- It stored *unavailability* as `user_id + starts_at/ends_at` (timezone-aware, half-open). No row meant available.
- The grid read it by finding the periods that overlap each event.
- Only admins could write it; in practice it came from a CSV matched to users **by first name**.

**Where it got mixed into scheduling:**

- The same database, with a foreign key to `users`
- Joined into the grid query
- Behind the scheduler's admin auth
- Blocked deleting users
- Planned as admin editing inside the grid (`web#3`)

**The cleaner split:** `heritage-media-availability` owns the volunteer-facing form and its own auth, and exports a monthly snapshot. The scheduler imports that snapshot read-only and never writes back. The only thing the two share is the person identifier.

**Draft contract** (a recommendation to decide on together, not final):

```text
month: YYYY-MM
responses: [
  person_key      # stable shared id (email or roster id), never a first name
  responded       # true even when they listed no conflicts
  submitted_at
  unavailable: [ local dates in America/New_York ]   # or tz-aware {starts_at, ends_at}
  notes?          # optional
]
```

**Decisions still open:**

1. Whole service dates or specific times?
2. What does "didn't respond" mean: available, or unknown?
3. Which field is the shared person key?
4. Is there a "prefer not to" level, or only can and can't?

---

## 7. Salvage list

### Reuse as-is (after review)

| What | Where | Why |
|---|---|---|
| Interval semantics and overlap check | API `app/services/queries.py:45-58`, `domain.py:169` | Correct and minimal. Fix the timezone handling. |
| Requirement level (required / preferred / optional) + `is_applicable` per slot | API `app/db/models/enums.py`, `event_assignments.py:12-18`; web `src/lib/domain.ts:17-30` | Real vocabulary from the workflow, with UI labels and colours. |
| Proficiency ladder (rank + `is_assignable`) | API `seed.py:45-54` | The basis for deciding who is eligible for a role. |
| Phone normalizer (E.164) | API `app/db/models/users.py:12-25` | Small and correct. |
| Test harness pattern | API `tests/conftest.py`, `tests/fixtures/seed_fixtures.py` | Throwaway schema, truncate per test, fixed IDs, error tables. |
| Error → HTTP status mapping | API `app/utils/exception_handlers.py:20-62` | Clean. Drop the traceback and request-body echo. |
| Grid-shaping logic | web `src/components/ScheduleGrid/hooks/useScheduleGridData.ts` | A pure function; pull it out and unit-test it. |
| Date formatters, default-month redirect, error/empty/skeleton components | web `src/lib/date.ts`, `ScheduleGridEntry.tsx:20-41`, `src/components/ui/*`, `skeletons/*` | Small, correct and generic. |
| Cache patch after save | web `src/queries/assignments.queries.ts:20-37` | Good pattern. Fix the hook-order bug and add error handling. |

### Reuse the idea (redesign the code)

- **The data model:** month schedule → events → one slot per role per event, plus roles, eligibility and team rotation.
  - Add `UNIQUE(year, month)` and NOT NULL times.
  - Define a slot template per event type.
  - Drop the forced user × role cross-product.
- **The rulebook in `seed.py` and the CSVs.** Turn it into a documented, tested, database-free function that generates a month's events and empty slots.
- **Assignment validation, built for the first time:**
  - the person is active
  - eligible for the role
  - not unavailable
  - not double-booked
  - optionally, on the event's team
- **Historical assignments (about 1,187 rows)** as test data for any future auto-scheduler. Keep them **private**, keyed by ID instead of first name.
- **The grid UI and its visual language.** Rebuild it with plain Tailwind, add save feedback, a clear option, eligible-only pickers and unavailability warnings, and make it mobile-friendly for volunteers.
- **One screen-shaped endpoint per screen.** If there's an API, generate the frontend types from its OpenAPI spec.
- **Decision records.** Move them out of issue comments into `docs/decisions/`.

### Leave behind

- The "platform" framing, the CRUD-for-every-table design, and the 11 near-identical routers.
- Any API key in the browser; the CORS/OPTIONS workarounds.
- The vendored Catalyst kit, hand-copied wide types, and unused client functions.
- Redis, rate limiting, workers and performance testing. The real load is about 8–15 events a month for about 16 people.
- Long-lived `staging` branches.
- Real personal data in any repo.

---

## 8. Lessons for the fresh start

1. **Write a one-page scope doc before code.** Name the user, the single job and the definition of done (for example, "November's schedule is published from this tool instead of the Google Doc"). Include an explicit **non-goals** list.
2. **Split by process step, with a contract between each step.**
3. **Rules engine first, as plain tested functions. Infrastructure last.** Design endpoints from screens, not tables.
4. **Choose the stack once and freeze it for v1.** At this size, SQLite or a single Postgres is plenty.
5. **Settle time semantics on day one.** A "day" is an America/New_York date. Test an evening event that crosses UTC midnight.
6. **Put constraints in the schema from the start.**
7. **Auth should match the audience.** Admin login on the server side, no secrets in the browser, and PII reads protected too.
8. **Ship to real users within the first week or two, on `main`.** Use it for a real month before adding anything.
9. **Day-one docs:**
   - `README`
   - `docs/scope.md`
   - `docs/domain.md` (glossary)
   - `docs/rules.md` (each rule linked to a test)
   - `docs/contracts/availability-input.md`
   - `docs/decisions/`
   - `.env.example`
   - CI that runs the tests

### Proposed project split (for discussion)

| Piece | Job | Status |
|---|---|---|
| **heritage-media-availability** | Volunteers submit conflicts for a month. Exports the monthly snapshot. | Exists |
| **heritage-media-scheduler** (this folder) | Generate a month's events and slots from the rulebook, assign people in the grid with validation warnings, and publish the result. | Fresh start |
| Roster (people, roles, eligibility, team rotation) | Reference data the scheduler reads. | Start as a config file inside the scheduler; promote it only if it outgrows that |
| Publishing / calendar export | Volunteer-facing view and `.ics` export. | Later. Your `hicc-media-calendar` skill already covers some of it |
| Auto-assignment | Suggest assignments from eligibility, availability and history. | Later. Needs validation rules and history first |
