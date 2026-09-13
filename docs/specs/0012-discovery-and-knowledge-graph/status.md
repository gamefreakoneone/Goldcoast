# Status: 0012 discovery and knowledge graph

Completed

## Evidence

- `python -m pytest tests/test_studio_discovery.py -q -p no:cacheprovider --basetemp output/pytest-0012`: 4 passed in 24.79s.
- `python -m ruff check .`: All checks passed.
- `python -m ruff format --check .`: 164 files already formatted.
- Transport fixtures validate Tavily basic search, extraction and caching. Replay raises before any provider/budget boundary on a miss. Failed records cannot be reissued. URL restrictions, verbatim source support, deduplication, conflicts and freshness are exercised.
- Official contracts: https://docs.tavily.com/documentation/api-reference/endpoint/search and /extract; https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/ . No paid calls were made during this spec.

## Shared design changes

Provider cassettes use exact request digests and retain pending/failed states conservatively. Graphs are typed PostgreSQL resource documents with source provenance and supported/disputed/stale edges. Sources expire after 24 hours unless a claim expires sooner. An excerpt match verifies provenance, not the semantic truth of a model interpretation; the campaign review retains that distinction.
