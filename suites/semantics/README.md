# Semantics

Structure is not behaviour. A migration can apply cleanly, and a catalog can
report the object, while the database still accepts rows the models forbid.

These suites declare constraints through the public model API, apply the
generated migration to a real server, and then try to violate them. They also
require that regenerating from unchanged models produces nothing at all, which
is the difference between a schema that converged and one that churns a little
more on every deploy.

| File | Question |
| --- | --- |
| `test_constraint_semantics.py` | Do declared `uniques` and `checks` reach the server, and does it enforce them? |
| `test_constraint_regeneration.py` | Does an applied schema stay converged, and does dropping one constraint touch only that constraint? |

The SQLite tests run in the fast tier because they need no container. The
PostgreSQL, MySQL, and MariaDB tests carry the `integration` marker.
