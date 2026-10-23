# Extending Family Agent

The FastAPI application owns family members, tasks, scheduling, and delivery state.
Service modules isolate external systems: `calendar_service.py` (Google/iCloud),
`weather_service.py` (Open-Meteo), and `school_calendar_service.py` (school days).
`regional_settings.py` provides validated installation settings to these modules
and the dashboard through `GET /settings/regional`. No family names belong in
application rules: use member IDs and roles.

The macOS worker is an optional platform adapter for Messages and Apple Maps.
Future delivery adapters should follow the existing claim/complete API, preserving
bounded retries and uncertain delivery handling. Optional Twilio and OpenClaw adapters now follow this flow; see
`MESSAGING_SETUP.md` for configuration and deployment. Calendar discovery is read-only; the explicit iCloud editing workflow supports confirmed writes with saved-field verification.

## Regional configuration

Set all five values in `.env`, then rebuild with `docker compose up -d --build`:

| Installation | Locale | Country | Time zone | Units | School calendar |
| --- | --- | --- | --- | --- | --- |
| India | en-IN | IN | Asia/Kolkata | metric | custom or none |
| UK | en-GB | GB | Europe/London | metric | custom or none |
| Germany | de-DE | DE | Europe/Berlin | metric | custom or none |
| USA | en-US | US | America/New_York | imperial | custom, none, or cobb |

Variables are `FAMILY_LOCALE`, `FAMILY_COUNTRY`, `FAMILY_TIMEZONE`,
`FAMILY_UNITS`, and `FAMILY_SCHOOL_CALENDAR`. The locale controls browser date
formatting; country scopes weather location searches. Time zone controls backend
calendar and reminder scheduling. Units control weather output, dashboard weather
threshold entry, and commute distances. The weather API's existing threshold
fields retain Fahrenheit for database/API compatibility; the dashboard converts
these values. Forecast responses include explicit unit metadata.

This is regional formatting, not translated content: interface labels, message
text, and Concierge parsing currently use English. Browser datetime input fields
use the browser's local time; macOS wake/intake/weekly maintenance schedules use
the Mac's system time zone. Keep the host and household time zones aligned.

Compose preserves US/New York and imperial formatting defaults. School filtering
defaults to `none`; existing Cobb installations must explicitly set
`FAMILY_SCHOOL_CALENDAR=cobb`. Copy `.env.example` before starting.

## School calendars outside Cobb County

Copy `examples/school-calendar.json` to `config/school-calendar.json`, enter your
school's verified date coverage and holidays, and set `FAMILY_SCHOOL_CALENDAR=custom`.
Weekdays are Monday=0 through Sunday=6, so different school weeks are supported.
The example is illustrative, not an official school calendar. Keep private calendar
files out of Git. The file is read at each check; expired coverage or invalid data
pauses filtered commutes rather than assuming an ordinary school day. `none`
disables school-day filtering; `cobb` retains the existing district PDF adapter.
Custom calendars require manual maintenance and do not download school holidays.

## Development

Use Python 3.12. Install `backend/requirements.txt` and `pytest` in a virtual
environment, then run `PYTHONPATH=backend:macos python -m pytest -q`.
The CI workflow runs this suite and checks dashboard JavaScript syntax.

This is an early framework foundation, not a supported hosted service. See the
README development status for authentication and migration limitations.

Save international iMessage contacts with their full country code (for example,
`+44…` or `+91…`). Matching preserves the country code. US installations also
accept their domestic ten-digit form with an optional leading `1`.

## Reuse and extension boundaries

The FastAPI composition root is `backend/main.py`. Domain state and validation
live in `models.py` and `schemas.py`; workflow modules handle planning, inbox
state, recurrence, scheduling, and reconciliation. Provider adapters isolate
calendar, weather, places, school calendars, LLM interpretation, and messaging.
The browser workspace and optional macOS/Windows helpers are clients of this API.

For another household, configure the existing modules rather than changing domain
rules. Member IDs and roles are the reusable identity boundary. For another
personal-concierge domain, add a domain module, its schemas and routes at the
composition root, with mocked provider tests. There is no automatic plugin loader.
Do not bypass the delivery claim/complete flow or treat provider acceptance as
proof that a recipient received a message.

`runtime_paths.py` resolves shared private storage without creating files on
import. `FAMILY_CONFIG_DIR` takes precedence over the compatibility variable
`CALENDAR_CONFIG_DIR`, then defaults to the checkout's `config/` directory for
native runs and `/app/config` in the supplied container. Explicit key-path and
messaging-config variables override the shared directory for those adapters.
`CALENDAR_CONFIG_DIR` remains an explicit calendar/cache override if both directory
variables are set. Keep runtime files outside version control.

## Release boundaries

The access layer provides one local administrator session and scoped bridge
credentials. It is not per-member authorization or hosted multi-tenancy. Keep
loopback port bindings. Database upgrades currently use startup SQL rather than
versioned migrations; validate changes against PostgreSQL before deployment and
back up existing databases and encryption keys before upgrading.

Unit tests set isolated database and configuration paths. They do not validate
live provider credentials, actual message delivery, Mac wake behavior, or a
PostgreSQL migration. CI checks Python behavior, both browser JavaScript files,
the OpenClaw hook, Windows script syntax, and disposable PostgreSQL startup and
API smoke checks. Run the container checks with:

```sh
docker build -t personal-concierge-v2:validation .
python3 tools/validate_container.py
```

The smoke runner uses randomly named containers and a private Docker network,
with no host port bindings or mounted data. It removes its temporary database,
including its anonymous volume, after the run.
