# Framework extraction review — October 23, 2026

## Findings

1. The current application includes modules and tests absent from the source
   repository index. A checkout of that index alone would omit access control,
   traffic reconciliation, calendar editing, and other imported modules. This
   workspace includes current source files and tests together.
2. Several adapters assumed `/app/config`, preventing ordinary native runs from
   sharing a writable configuration directory. Shared runtime path resolution now
   covers access keys, encryption, calendars, school calendars, event caches, and
   messaging. Existing explicit adapter overrides remain supported.
3. Fresh US installs implicitly selected a specific Georgia school district.
   Both application and Compose now default to no district. Cobb is opt-in.
4. CI omitted the newer concierge workspace JavaScript. Syntax checking now covers
   both browser JavaScript files.

## Validation

- Python 3.14.7: 215 tests and 8 subtests passed, including new configuration and
  import-isolation regressions. CI and the production Dockerfile target Python 3.12.
- Both browser JavaScript files passed Node syntax checks.
- OpenClaw hook passed 6 scenarios without sending messages.
- Python source compilation and platform shell syntax passed.
- Dependency consistency check passed.
- Production Docker image built successfully on Python 3.12.
- Disposable PostgreSQL 16 smoke test passed for initial and repeated startup,
  health, authentication, regional defaults, and an encrypted member round-trip.
  The test removed its containers, database volume, and private network.
- CI now runs the same container build and PostgreSQL smoke test.

## Remaining limits

The reusable foundation retains the family domain model, API names, and platform
helpers. It does not implement arbitrary agents, multi-tenant isolation, or a
plugin registry. Database startup includes PostgreSQL-specific additive SQL;
The fresh-schema smoke test does not establish compatibility with every legacy
database migration. Dependencies are
not fully locked. Fixed Compose container names and ports prevent side-by-side
stacks without configuration changes. These are follow-up engineering tasks,
not capabilities claimed by this extraction.

No source deployment, household configuration, database, or provider account was
modified. No live calendar writes or messages were exercised. GitHub authentication was verified outside the sandbox. Publication still
requires a destination repository.
