# Technical debt register

Record only a concrete compromise with a demonstrable effect and a closure condition. “Improve the code” is not a task.

| ID | Area | Observable risk/cost | Evidence | Closure condition | Priority | Owner |
|---|---|---|---|---|---|---|
| TD-001 | ml/features | The three recorded feature digests live only in `ml/README.md` and the completed plan; no test pins them, so a future change can move them silently and the documented determinism evidence goes stale without any check failing | The lead reproduced `7e412bb0…`, `b3ad914c…`, `408d4580…` by hand on 2026-09-25; `grep` finds them in documentation only, never in `ml/tests` | A test asserts the three digests for the committed fixture, or the digests are removed from the documentation in favour of the relative determinism assertions that already exist | P2 | TASK-058 |
| TD-002 | backend/db | `stops.name` carries `UniqueConstraint("name")`, but real stop names are not globally unique; seeding real stops would reject rows, and any name-keyed join would merge distinct places | The committed OSM extract has 382 names on more than one node (349 on two, 19 on four, 11 on three, one each on five, six and ten); the synthetic catalog gives two different stops the name "Тестовая площадь" deliberately | The constraint is dropped, or replaced by one that matches the real key, before the first real stop rows are seeded | P2 | TASK-032 |
