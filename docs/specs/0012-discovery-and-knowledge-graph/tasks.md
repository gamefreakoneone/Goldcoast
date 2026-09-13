# Tasks: discovery and knowledge graph

- [x] Read requirements and design.
- [x] Implement bounded provider cassettes and Tavily/Ticketmaster adapters.
- [x] Implement typed evidence graph, provenance, deduplication, conflicts and freshness.
- [x] Test recorded provider requests, exact replay, unsafe extraction, source support and stale claims.
- [x] Update design, status, documentation and commit.

## Validation Steps

`python -m pytest tests/test_studio_discovery.py -q -p no:cacheprovider --basetemp output/pytest-0012`

`python -m ruff check .`

`python -m ruff format --check .`

Expected: provider transport fixtures never access the network, replay never calls transport or reserves usage, unsupported URLs/citations fail and graph conflicts are visible. Optional provider absence returns a labeled unavailable result.
