# Release Provenance

Release provenance makes a harness result attributable.

`harness/provenance.py` records:

- Python version
- Python implementation
- Platform string
- dbwarden distribution version
- dbwarden installation location
- Console entry points
- Optional plugin distribution versions and locations
- Lockfile path and SHA-256 digest

The distribution isolation test rejects a dbwarden location inside the source
checkout supplied to the assertion. The black-box boundary test rejects private
dbwarden imports in harness source.

## Why this is required

Without provenance, a passing integration test can be attributed to the wrong
wheel, a local editable install, or an accidental dependency upgrade. With it,
the same command can be rerun against the same release environment.
