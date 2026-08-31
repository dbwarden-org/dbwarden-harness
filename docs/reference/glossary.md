# Glossary

**Black box**
: A test boundary that uses public inputs and outputs without importing private
  implementation details.

**Consumer project**
: A temporary project directory containing dbwarden configuration, model files,
  migrations, and database state.

**Drift**
: A semantic difference between expected model state and observed database
  state.

**Provider**
: A lifecycle object that starts, resets, diagnoses, and stops a disposable
  database.

**Reference schema**
: A checked-in model fixture plus expected table and index metadata.

**Round trip**
: Generate migrations, apply them, reverse engineer the live database, reload
  generated models, and require convergence.

**Enforcement**
: Evidence that the server refuses a write the declared constraints forbid, as
  opposed to evidence that the constraint appears in a catalog.

**Regeneration silence**
: The requirement that regenerating from unchanged models produces no
  migration. Its absence is schema churn: correct SQL, applied forever.

**Semantic snapshot**
: A normalized representation of live database objects used for comparison.

**Experimental cell**
: A matrix test that runs and retains evidence but is allowed to fail because a
  known package compatibility issue exists.

**Fast tier**
: Tests that run without Docker, using SQLite or generated artifacts only.
  Selected by `pytest -m "not integration and not slow"`.

**Integration tier**
: Tests that require a container from `infrastructure/providers`. Selected by
  `DBWARDEN_HARNESS_RUN_INTEGRATION=1 pytest -m integration`.

**Slow tier**
: Tests that require a container and significant time. Selected by adding
  `-m slow` explicitly.

**MCP server**
: An interactive testing server that provides workspace management, warm
  connection pools, and bug report collection for consumer workflows.
