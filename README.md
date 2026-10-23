# Personal Concierge V2 framework

This repository packages the current Family Agent application as a reusable,
self-hosted concierge foundation. Households supply their own directory, contacts,
calendar credentials, regional settings, school calendar, and messaging provider.
No household configuration, database, credentials, or backups are included.

The implemented scope remains a family/personal concierge. It is not a
multi-tenant platform or an arbitrary-agent plugin runtime. See
[FRAMEWORK.md](FRAMEWORK.md) for extension boundaries and
[IMPLEMENTATION_REVIEW.md](IMPLEMENTATION_REVIEW.md) for review findings and validation.

Native Python adapters share a checkout-local `config/` directory by default;
set `FAMILY_CONFIG_DIR` to relocate it. Containers use `/app/config`.
Existing adapter-specific path variables remain supported. A new installation
uses no school district filter unless explicitly configured. Messaging workers
are optional and must be configured before enabling their Compose profiles.

Do not run this Compose stack alongside another Family Agent stack with the same
fixed container names or host ports. This extraction preserves those names for
the existing platform helper scripts. Docker/PostgreSQL is the supported full
application runtime; SQLite is used only for isolated unit tests.

---

# Family Agent

Family Agent is a self-hosted family dashboard for tasks, calendars, departure
planning, and private reminders. FastAPI and PostgreSQL run in Docker. Calendar
credentials and family data stay on the computer running the installation.

## Current features

- Family members and assigned tasks
- Task due dates and optional iMessage reminders
- Weekly recurring tasks that advance after each completion
- Read-only Google and iCloud calendar views
- Family calendar assignments for personalized daily briefings
- Calendar overlap checks
- Home-based departure and return-route planning
- Scheduled, traffic-aware work and school commute texts for selected parents and weekdays
- Optional school-day filtering through custom calendars or the Cobb County adapter
- Scheduled and automatic calendar reminders through macOS Messages
- Three-day weather guidance for clothing, rain gear, wind, and sun protection
- Personalized daily iMessage briefings with activities, tasks, weather advice, and an uplifting thought
- Seven-day morning briefing ledger with same-day outage recovery and bounded delivery retries
- Weekly validation with bounded recovery for local services and private configuration
- Optional macOS wake schedule for reliable 7:00 AM briefings
- LangGraph-powered Concierge Inbox previews for family texts and emails
- Private iMessage intake: saved family contacts can prefix a reply with `FA` to request a Concierge plan

## Start locally

1. Copy `.env.example` to `.env` and replace the database password.
2. Run `./preflight.sh` to check prerequisites, then `./start.sh` to check again and build/start the app.
3. Open `http://localhost:8000/dashboard`.

The web application listens only on `127.0.0.1`. PostgreSQL is available only
inside the Docker network. Calendar setup is documented in `CALENDAR_SETUP.md`.

## Private configuration

Do not commit `.env` or anything inside `config/` except `.gitkeep`. Google OAuth
tokens, the Google client file, and the iCloud app-specific password are stored
there and are excluded from both Git and Docker build context.

Family roles and ages are managed under **The family** in the Tasks tab. Ages,
iMessage phone numbers, and Apple Account emails are encrypted before database
storage with a local key in `config/family-secrets.key`; that key is excluded
from Git. The Concierge uses the profile to expand requests such as “notify
parents” and require an identified parent driver for a family member under 18.
For appointments and location-based tasks, its review also records whether the
child needs drop-off and pickup, pickup only because they are already at school,
or no transportation. Pickup can be assigned to either saved parent, Uber, or
Undecided. Task plans keep that transportation decision in the task details.
Back up `config/family-secrets.key` with the app data; encrypted ages and contacts
cannot be recovered if that key is lost.

The iMessage bridge requires macOS with Messages signed in. Other platforms can
run the dashboard and calendar features; optional Windows/Linux WhatsApp and SMS adapters are documented in `MESSAGING_SETUP.md`.

### Commute traffic texts

The Departures tab can store separate work or school commute schedules for each
parent. Choose the recipient, destination, check time, and any combination of
weekdays. Add another schedule when a parent needs a second check time. Destination
addresses are encrypted in PostgreSQL with the same local family secrets key used
for contact details.

At a due time, the macOS worker asks Apple Maps for the current driving time and
queues a private iMessage with the ETA, distance, and a directions link. This uses
the Mac's built-in routing service and does not require a paid Maps API key. If a
traffic calculation fails, the text includes a live directions link instead.

Google Places address suggestions are optional. Enable billing and **Places API
(New)** in a Google Cloud project, create an API key restricted to that API, and
add it to the private `.env` file as `GOOGLE_PLACES_API_KEY`. After rebuilding, the home, work,
and school address fields suggest matching US addresses as you type. The key is
used only by the backend and is never included in dashboard JavaScript or URLs.
Manual address entry continues to work without it.

School schedules can follow the official Cobb County school calendar. Family Agent
refreshes and parses the district's staff-use calendar each week, then skips weekends,
school breaks, closed days, student holidays, and digital learning days. The verified
2026–27 source is the [Cobb County School District staff-use calendar](https://media.cobbk12.org/media/WWWCobb/medialib/2026-2027-staff-use-calendar.6d50b7128535.pdf).

### FA-prefixed iMessage requests

The same Mac bridge can distinguish messages for the Concierge from personal
replies. Incoming messages are ingested twice daily, at 7:05 AM and 7:00 PM;
messages received between scans remain in the local Messages database until the
next window. A new message from an enabled, saved family contact enters the
Concierge Inbox only when it begins with `FA `, `FA:`, `FA-`, or `FA,`. Examples:

- `FA schedule a dentist appointment tomorrow at 3:30 PM for Alex`
- `FA: remind me to bring my rain jacket`

Messages without that prefix are ignored. Unknown and disabled contacts are also
ignored. The first inbox scan starts at the newest message, so existing message
history is never imported. Requests and proposed plans are encrypted in PostgreSQL;
the sender's handle is used only to match a saved contact and is not copied into
the inbox record. Plans wait in the dashboard for review. The bridge does not send
an automatic reply or create tasks, calendar events, or notifications. Creating a
reviewed task marks its source request handled; irrelevant requests can be dismissed.

Reading new messages requires macOS **Full Disk Access** for the Python executable
shown by `./install-imessage-alerts.command`. Re-run that installer after granting
access. This permission is only needed for the incoming `FA` feature; outgoing
scheduled alerts continue to work without it.

### Local Concierge interpretation

Only `FAMILY_LLM_PROVIDER=ollama` or `none` is supported. OpenAI cloud interpretation has been removed. To use the existing local model:

```ini
FAMILY_LLM_PROVIDER=ollama
FAMILY_LLM_MODEL=qwen3.5:9b
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Use `FAMILY_LLM_PROVIDER=none` for deterministic parsing without an LLM. Remote Ollama URLs and cloud-labelled models are rejected; redirects and HTTP proxies are disabled for interpretation. Keep the configured Ollama instance on your Mac and use a locally downloaded model. Family requests still reach explicitly configured calendar/messaging providers when those integrations are used; this change concerns LLM interpretation.

### Morning wake on macOS

Run `./install-morning-wake.command` once to schedule a daily 6:59 AM wake. The
installer uses macOS `pmset`, asks for the Mac administrator password, and shows
the resulting schedule. Keep a Mac laptop connected to power; a closed lid can
prevent a scheduled wake. The Family Agent worker holds the Mac awake while it
creates and delivers the 7:00 AM briefings. Normal idle-sleep settings take over
afterward, so an actively used Mac is not forced to sleep.

macOS supports only one repeating power-event pair. If another repeating power
schedule is already present, the installer displays it and asks before replacing
it. Run `./remove-morning-wake.command` to remove a matching Family Agent wake.

The Alerts tab keeps a seven-day morning briefing ledger for every enabled
recipient. If the Mac or local service misses 7:00 AM, the briefing remains due
for the rest of that calendar day and is queued when the service returns. Calendar
and weather connection failures remain in a waiting state and retry automatically.
An iMessage handoff that reports failure is retried up to three times, five minutes
apart. A `Sent` result means macOS Messages accepted the message; Apple does not
provide this local bridge with a recipient delivery receipt.

### Weekly validation and safe recovery

The existing macOS worker runs a validation each Sunday after 7:00 AM. It checks
the Docker services, API, database, calendar connections, weather service, private
file permissions, and iMessage background service. It can start stopped containers,
restart an unresponsive API, and restore private file permissions. The latest result
appears in the Alerts tab, with any issue that needs manual review.

The loop never updates application code, changes credentials, deletes data, or
rebuilds containers automatically. Its privacy-safe summary is stored locally in
`config/self-healing-state.json`, and a short history is kept in
`config/self-healing.log`; both paths are excluded from Git.

## Development status

This is an early local-first build. Authentication, versioned database migrations,
backup and restore commands, pluggable AI providers, and release packaging must be
completed before exposing it on a network or distributing it as a supported product.

## Reuse and regional settings

Family Agent is available under the [MIT license](LICENSE). Start from a fresh
clone, copy `.env.example` to `.env`, set a database password, and choose your
locale, country, IANA time zone, measurement units, and school calendar provider.
See [FRAMEWORK.md](FRAMEWORK.md) for India, UK, Germany, and USA examples,
architecture, extension points, and development commands.

On installations that need the legacy Docker builder:

```sh
DOCKER_BUILDKIT=0 docker compose up -d --build
```

Never upload your live `config/`, `.env`, backups, database, or calendar credentials.
Public releases should contain only the source and synthetic examples.


## Dependency preflight

Install Docker with Compose first. On macOS/Linux, run these commands from the
package directory (on Windows use a WSL shell with Docker Desktop integration):

```sh
./preflight.sh           # Dashboard dependencies only; no host Python required
./preflight.sh --macos   # Also check host Python and Apple tools for the bridge
./preflight.sh --intake  # Also check read access to the local Messages database
./start.sh               # Stop on failed checks, otherwise build and start
```

For the legacy Docker builder use `DOCKER_BUILDKIT=0 ./start.sh`.
The macOS refresh shortcut and bridge installer also run preflight automatically.
Running `docker compose up` directly bypasses preflight, but a missing or empty
database password is still rejected by Compose.

The checks report PASS, FAIL, and NOTE, and return a nonzero exit code for required
failures. They check package files, writable configuration, `.env`, the example
password, Compose configuration, Docker availability, cached base images, and
container-name conflicts. They do not install software, download images, change
settings, print credentials, or send messages. Optional incoming-message checks
read database schema only. Internet downloads, free port availability, registry
credentials, Messages sign-in/automation approval, background Full Disk Access,
and successful service startup still need to work at runtime. This is a dependency
check, not a guarantee of delivery or full application health.


## Optional Windows and dedicated-number messaging

See [MESSAGING_SETUP.md](MESSAGING_SETUP.md) for Windows PowerShell startup,
OpenClaw WhatsApp linking, Twilio SMS/WhatsApp, and a separate household sender
number. Includes private configuration examples, recipient opt-in restrictions,
signed webhook ingress, an OpenClaw FA-message hook, and no-send configuration
checks. New transports are disabled by default. Provider accounts, numbers,
approved WhatsApp templates, and live delivery testing must be completed separately.

### Local Ollama Concierge

Set `FAMILY_LLM_PROVIDER=ollama`, `FAMILY_LLM_MODEL=qwen3.5:9b`, and
`OLLAMA_BASE_URL=http://host.docker.internal:11434` in the private `.env`, then
recreate the API container. Ollama runs on the Mac; Docker connects through
its host gateway. No Python dependencies are installed on the Mac. Requests
go to the configured Ollama server, with no OpenAI fallback. Keep Ollama running
for interpretation; failed requests fall back to the deterministic parser.

### Concierge clarification conversations

New FA requests use `backend/concierge_template.json` for classification instructions and missing-detail questions. A calendar draft requires an activity/title, family member, date and start time, plus any required driver/pickup information from the private family profile. End times and locations are optional in this version. Questions ask for one missing detail at a time. The final acknowledgement says the draft is ready for review, never that it is booked.

Reply to a question with its number, e.g. `FA #42 tomorrow`, then `FA #42 3:30 pm`. The sender must match the original request's saved contact. Unprefixed personal replies are ignored. Normal requests retain morning/evening ingestion; numbered replies are checked on each minute's bridge run while the Mac and app are available. The dashboard also provides a **Send answer** form on incomplete incoming requests; dashboard answers do not send an extra text.

Draft answers are stored inside the encrypted plan. A receipt table makes re-ingestion idempotent so the same reply does not queue another question or acknowledgement. Known dates stay anchored when replies arrive on another day. Saving a completed conversation retains its captured details. Existing drafts are not automatically messaged or modified by this update.

### Chained LLM workflow

Dashboard previews and incoming requests now share `concierge_chain.py`: interpret with the configured LLM → classify/extract using the existing family rules → merge confirmed details → validate → ask for missing details or acknowledge a draft ready for review. Each numbered reply resumes that chain using the encrypted inbox plan. Each turn makes one interpretation call; a model outage uses the existing local fallback. The saved plan records the workflow path and whether the current turn used the model or fallback. Database writes and reply queueing remain in the API transaction outside the graph, retaining duplicate protection. The graph itself never creates tasks, modifies calendars, or sends messages. The local deployment uses `qwen3.5:9b` for the shared workflow. `gpt-oss:20b` remains installed for manual comparison; it is not called automatically.

### Active testing and hourly FA ingestion

The Mac bridge reads `config/imessage-ingest.json` on each run. Use `{"mode":"testing"}` to check new FA requests every minute during active testing, `{"mode":"hourly"}` for one check per clock hour, or `{"mode":"scheduled"}` for the original morning/evening checks. Mode changes take effect on the next bridge run without reinstalling or rebuilding Docker. Existing numbered conversation replies remain eligible each minute. The private cursor and API receipt ledger are retained when changing modes. Testing mode stays enabled until explicitly changed; it does not expire automatically. The Mac, Messages access and Docker must be available.

Agent replies use the reserved `Family Agent request #…:` heading. Both the Mac bridge and API ignore incoming echoes of that heading and the older `FA request #…:` heading, including self-messages. A user can place `FA #10` at the beginning or end of a numbered reply; unmarked personal replies remain ignored.

### Events: Atlanta concert discovery

Open `/dashboard#events` and select **Refresh events**. The app reads public MusicEvent listings from the Tabernacle, Coca-Cola Roxy and Ameris Bank Amphitheatre, showing remaining dates in the current calendar year in Atlanta time. Search by artist/venue/published genre, filter by month, and save a shortlist locally. This is selected venue coverage, not every Atlanta concert; listings may include solo artists and tribute acts. Prices and age limits remain unknown when not published. No family information is sent to these sites.

Refreshes are on demand, limited to once per minute. Failed sources retain their previous results with an outdated-data warning. Official links let you verify availability and cancellation details. Shortlisting does not purchase tickets, create calendar entries or send messages. Concierge now recognizes discovery requests such as “FA find rock concerts in Atlanta in November”, refreshes the selected venues, and returns results in the preview and an incoming FA reply. Search supports month names, artist/genre keywords and the current year; it uses deterministic filtering without an LLM call. Calendar/transport handoff remains follow-up work. State persists in `config/concert-discovery.json`; no additional API key or Python dependency is required.

Concert preferences are available inside Events: favorite artists or genres (either can match), maximum published USD ticket price, whether to include unknown prices, and explicitly all-ages listings. Enable them for Concierge searches and optionally filter the Events list to matching entries. Explicit artist/genre search terms override music favorites, while enabled budget and admission filters remain active. Price availability and content suitability are not inferred. Preferences are saved locally alongside the shortlist and do not change household profiles.

### Appointment traffic and waking the Mac

Located, busy, timed calendar events offer optional home-to-appointment traffic checks when home and calendar alerts are enabled. New events default to off: select “Get traffic alerts for this event” in Departures, choose recipients, then save. Previously saved settings are preserved. The Mac worker checks two hours ahead, then every 15 minutes (five minutes after a route failure). It sends a fresh estimate at the earlier of 45 minutes before the appointment or travel time plus the saved arrival/parking buffers. If the appointment is added late, checks catch up while it is still upcoming. No duration is invented when routing fails. Fixed “Time to leave” alerts are replaced; ordinary appointment reminders remain.

Departures shows the last estimate and lets you choose traffic recipients or disable driving reminders per appointment. Until selected, the existing calendar-alert recipient is used. Removed events are cancelled after a complete calendar refresh. Partial calendar refreshes suspend traffic claims to avoid acting on uncertain events. Very long routes can already be overdue when checks begin two hours ahead. Estimates depend on the Mac, connectivity and provider availability; they are not delivery guarantees.

For sleep wakeups, run `./install-appointment-wake.command` on the Mac and approve its administrator prompt. The installer copies a root-owned, wake-only helper and LaunchDaemon; it does not run project code as root. It polls the local app for at most ten future wake timestamps, replaces only its own tagged wake events, and preserves the 6:59 AM repeating schedule. The helper does not receive event titles or addresses. Wakeups begin one minute before the next check. Keep the Mac powered, logged in and Docker running; a closed lid or shutdown may prevent operation. Without this optional installation, traffic checks run only while the Mac is awake.

Apple live traffic was verified through the existing worker's September 14 outbound and return alerts (25 and 27 minutes respectively). A direct diagnostic from the coding tool returned an unknown MapKit geocoding error; this does not establish a failure of the background worker.

### Local archive and iCloud editing

The Calendar API hides observed events one hour after a known end time when calendar sources are complete. Encrypted local snapshots support the Past events view for 90 days; old snapshots are purged during successful calendar maintenance. Maintenance runs through normal calendar-alert polling even if alert delivery is disabled, and when Calendar is opened. It captures the available calendar window (including the previous day); it does not backfill every historical event. Missing end times and incomplete refreshes defer cleanup. Provider events are never deleted by archiving. Completed calendar reminder occurrence markers are retained to avoid duplicate delivery. Existing traffic expiry/cancellation and calendar reminder cleanup stop outstanding work for past occurrences.

Calendar now has an explicit iCloud create/update form with a selected connected calendar and device-local start/end times. Duplicate Family calendars are numbered in connection order. Creates use a stable request UUID and conditional creation to prevent retry duplicates; updates use an ETag to reject stale forms. Saves are checked by reading back the resource. The first version supports individual timed events only: recurring, all-day, and invitation-bearing events must be edited in Apple Calendar. No delete or invitation-sending endpoint is provided. Google remains read-only. Saving an editor form is an external calendar write; archiving is only local.

### Unified Concierge workspace

Concierge is the default home. Our agenda combines open tasks and connected calendar events with date/person filters, List and Calendar layouts, and an Unscheduled task section. Old Tasks and Calendar links lead into the agenda. Family settings holds profiles, contacts, calendar assignments, home/commute settings, weather preferences and automatic reminder preferences.

Website requests use `/concierge/requests` to create an encrypted, persistent request with a retry identifier. Replies use the same saved-dialog workflow as incoming FA messages. Browser requests do not send an iMessage acknowledgement. Needs attention shows pending requests; History shows saved/dismissed requests and completed tasks. A saved draft is explicitly separate from an actual task or calendar save.

The activity panel supports task edits/status changes and the iCloud editor, plus linked reminder status and appointment traffic controls. Creating a task from a request records its task ID transactionally. Creating an iCloud event from a request uses a stable provider UID and records a receipt; retries cannot create a second event with that identity. If iCloud accepts a write but the receipt cannot be saved locally, the conditional write blocks a duplicate and requires checking iCloud before retrying. Multi-event requests are saved individually. Existing iCloud series/invitations still require Apple Calendar; Google remains read-only. Selecting a person filters appointments by calendar assignments, not inferred event attendance. Archived provider events remain intact.

### Local dashboard sign-in

The dashboard and private API routes now require authentication. On the Mac, open
`open-dashboard.command` to exchange the local key for a seven-day HttpOnly,
SameSite browser session. The key stays in `config/dashboard-access.key` (mode 600);
never commit or share it. Browser writes require the dashboard request header and
reject unrelated origins. Workers use a bearer credential. Remote messaging bridge
credentials are restricted to their inbox, sync, claim, and acknowledgement routes.
This is a local administrator session, not per-family-member permissions or a
public HTTPS deployment. Keep the API bound to localhost.

After this security update, run `./install-appointment-wake.command` once to install
the authenticated root-owned appointment wake helper. The daily morning wake is
separate. Without reinstalling, the older helper cannot read the protected wake
plan. For local API diagnostics, read the access key privately and send it as a
bearer header; do not print it in logs.

Calendar saves compare the provider readback with the requested calendar content.
A verification error may mean the event was written: refresh before taking further
action. Creates retain a stable identifier so an exact verified retry does not
create a second event. Concierge request saves revalidate missing details on the
server before calling the calendar provider.
