# Django Adoption Fixture

This fixture represents a Django-managed database handed to DBWarden. The
adoption flow is: inspect the existing schema, reverse-engineer public models,
create a DBWarden baseline, and validate the next model change without
rewriting the existing migration history.
