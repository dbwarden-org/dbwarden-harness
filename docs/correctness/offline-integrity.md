# Offline Integrity

Offline checks validate artifacts that DBWarden uses without a live database.

## State manifests

`tools/offline_integrity.py` finds model-state JSON files, calculates SHA-256
digests, writes a sorted manifest, and verifies that actual files match the
recorded values.

## Covered behavior

- A state manifest can be generated.
- Unchanged state verifies successfully.
- Changed state reports the affected paths.
- Missing state is reported as an assertion failure.
- Manifest files are excluded from their own input set.

## Why this matters

Offline generation depends on files that may be committed, cached, or moved
between jobs. A stale state file can make a migration appear deterministic
while using a different input. Checksums make the dependency visible.
