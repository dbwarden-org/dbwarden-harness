# Glossary

**Black box**
: A test boundary that uses public inputs and outputs without importing private
  implementation details.

**Consumer project**
: A temporary project directory containing DBWarden configuration, model files,
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

**Semantic snapshot**
: A normalized representation of live database objects used for comparison.

**Experimental cell**
: A matrix test that runs and retains evidence but is allowed to fail because a
  known package compatibility issue exists.
