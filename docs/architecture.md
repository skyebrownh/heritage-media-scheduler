# HICC media ops: separation of concerns and data ownership

This doc covers how the church media tooling is split into separate projects, which project owns which data, and how data moves between them. Decided on 2026-10-18, after the [StewardHQ audit](stewardhq-audit.md). Updated on 2026-10-19 to match the scheduler's [SPEC.md](../SPEC.md), which wins where they differ.

**Guiding rule:** each project does one job, owns its own data, and shares data only through a defined contract. Everything is built for HICC media specifically, not as a general platform.

---

## The pieces

| # | Project | Job | Reads | Produces | Does not |
|---|---|---|---|---|---|
| 1 | **heritage-media-availability** (built, launches 2026-10-25) | Volunteers submit the whole days they can't serve each month | — | People list and monthly submissions (as copy text today; a read-only JSON endpoint is planned) | Schedule anyone, or store roles |
| 2 | **Media requests** (being redesigned outside these repos) | Turn requests into special events that need media coverage | — | Special events for a month | Assign people |
| 3 | **heritage-media-scheduler** (starting) | Build a month's schedule: generate services and slots, check them against the rules, fill them | 1, 2, its own roster details and rulebook | A month's schedule in its own database, shown on a schedule page behind Skye's admin login as a table shaped like the Doc | Collect availability or requests, talk to Google, offer pages to volunteers, or send notifications |
| 4 | **Schedule UI** (deferred) | One page that replaces the Google Doc | 3's output | An edited and published schedule | Make scheduling decisions |

**For now, the Google Doc stays Skye's job.** The scheduler's job is *deciding* who serves. It shows its answer on a schedule page, as a table shaped like the Doc, and Skye moves it into the month's Doc herself. Automating that step, or building piece 4, waits until it's clearly the bottleneck.

---

## Who owns which data

**There is no central database.** Each fact has exactly one owner. Other projects receive a copy through a contract and never write it back.

| Data | Owner | Notes |
|---|---|---|
| Who people are (first and last name, active) | **Availability** (`members`) | Members are deactivated, never deleted, so `member.id` stays stable. |
| When people can't serve | **Availability** (`submissions`) | Whole days, Eastern time. Every version is kept, and the newest one per person and month counts. |
| Media details about people (roles, proficiency, team Alpha/Omega, pairings) | **Scheduler** | Availability's SPEC lists roles as a non-goal that "belong to the scheduling side". Keyed by `member_id`, with no names stored. |
| The rulebook (service times, rotation, exceptions, slot templates per event type) | **Scheduler** | Stored in the scheduler's database with effective dates, and edited in its admin. The engine that applies it is tested code. |
| Special-event requests | **Media requests** | Its shape is set by the new process. |
| Published schedules | **The month's Google Doc** (made by Skye) | The scheduler's output is a proposal. The Doc is the final word. Skye can re-import a Doc after editing it, so the scheduler's copy matches. |
| Historical assignments | **Scheduler**, in its hosted database (never in git) | Skye's Docs from Aug 2025 to Oct 2026, imported with name matches she confirms. StewardHQ's database and earlier Docs aren't imported. |

### The shared person key

`member.id` from the availability app is the one identifier every project uses. **No project ever matches people by name.** StewardHQ's CSV import matched people by first name, which is what this rule prevents.

---

## How data moves between projects

**Availability → scheduler: a read-only JSON endpoint on availability** (decided 2026-10-18).

- **Why not the copy text:** availability's copy output uses display names (first name, plus a last initial only when two people share a first name) and has no `member_id`. A scheduler that parsed it would be matching people by name, which is exactly what failed in StewardHQ.
- **Why now, not later:** building the scheduler against the endpoint's shape from the start means its input never has to be reworked.
- **Timing:** build it as its own issue in the availability repo **after the October 25 launch**, so the launch isn't put at risk. The scheduler's first stages (rulebook, roster, generate) don't need live availability, so they aren't blocked. History import needs the member list, so the endpoint comes before it. Their tests use fixture JSON in the endpoint's shape.
- **Security:** it's protected by a token that only the scheduler holds. Calls go machine to machine, never from a browser. The token lives in an environment variable on each side.

**Direct reads of another project's database: never.** Django's migrations own availability's tables, so reading them directly would tie the scheduler to table names that can change at any time. Railway can connect several services to one Postgres, but we're choosing not to.

---

## Contracts

### Availability → scheduler

This is a draft shape for the endpoint, taken from availability's SPEC (`members`, `submissions`). The exact design belongs to that repo's issue:

```text
GET <availability>/api/months/<YYYY-MM>     (header: token)

month, is_closed,
members:     [ id, first_name, last_name, is_active, standing_availability ]
submissions: [ member_id, kind (days | available_all | unavailable_all),
               days (day numbers, empty unless kind = days), notes, submitted_at ]
             # only the current (newest) submission per member
```

- **No submission for a month means the person didn't respond.** It does not mean available. "Available all month" is a submission of its own.
- **Days are calendar dates in Eastern time,** with no times of day.
- `standing_availability` (for example "3rd Sundays only") is free text, so the scheduler treats it as a note for Skye, not as a rule. Structured recurring rules are on availability's "Later" list.

### Media requests → scheduler (draft, to firm up when the new process exists)

```text
date, start time, end time (Eastern), event type, title,
roles needed (with required / preferred / optional), notes
```

Until the new form exists, Skye enters special events in the scheduler's admin.

### Scheduler output (updated 2026-10-19)

The scheduler is a Django app on Railway with its own Postgres. Its output is a **schedule page** behind Skye's admin login. It shows a table that mirrors the Doc's schedule table (date rows including Saturday prayer and special events; ProPresenter, Sound, the four camera columns, On Call, Unavailable, Notes), followed by the team counts, the Unavailable list, `check`'s findings and `fill`'s tie report.

**Skye does the Google Doc part,** as today. Tip: a table selected in a browser and pasted into Google Docs usually arrives as a real table, so the hand step can be one copy-and-paste rather than retyping.

**Later, only if the hand step becomes the bottleneck:** a separate renderer could write the Doc directly from the scheduler's schedule data (Google Docs API or Apps Script). It's not in scope now.

---

## Guardrails (lessons from StewardHQ)

- **HICC-specific names** (`MediaRole`, `hicc_rotation`), not generic ones (`Resource`, `Ministry`).
- **Rule of three:** generalize only after needing the same thing three times.
- **Every project states what it does *not* do,** in its SPEC.
- **No secrets in browsers,** and no real personal data in any repo. Roster details are keyed by `member_id`, and repos stay private.
- **The scheduler is hosted on Railway with its own Postgres,** behind Skye's admin login. It talks only to availability's endpoint, and has no Google integration and no pages for volunteers.
