# Research: Discourse Post Archiver

## Language & Runtime

**Decision**: Python 3.11+

**Rationale**: Python 3.11 ships `tomllib` in the standard library, eliminating the need for
a TOML parsing dependency. Signal handling (`signal.SIGINT`), file I/O (`pathlib`), JSON
state files, and argument parsing (`argparse`) are all stdlib. The ecosystem has mature,
reliable libraries for the two non-stdlib requirements (HTTP and HTML conversion). Python
is well-suited to scripting-style CLI tools of this nature.

**Alternatives considered**:
- Go: Excellent stdlib HTTP support and fast binaries, but no TOML stdlib and
  HTML-to-Markdown libraries are less mature. Binary distribution is a benefit but not
  a requirement here.
- Shell + curl: Too fragile for pagination, retry logic, and structured state management.

## HTTP Client

**Decision**: `requests` (3.x, latest stable)

**Rationale**: The Discourse API requires auth headers on every request, pagination across
multiple endpoints, and retry-with-backoff logic. `requests` provides `Session` objects
for shared headers, clean response handling, and timeout support with minimal boilerplate.
It is the most widely adopted Python HTTP library with a long stable history.

**Alternatives considered**:
- `urllib` (stdlib): Functional but requires significant manual boilerplate for sessions,
  headers, and retries. Not worth the complexity for a network-heavy tool.
- `httpx`: Supports async but sequential downloads make async unnecessary. Adds complexity
  for no benefit here.

## HTML to Markdown

**Decision**: `html2text` (latest stable)

**Rationale**: Discourse post bodies are returned as HTML. `html2text` is the de-facto
standard Python library for HTML-to-Markdown conversion. Simple API: one function call
per post body. Well-maintained and widely used.

**Note**: Where the Discourse API supports `include_raw=1`, raw post content (already
Markdown) is used directly, bypassing HTML conversion entirely. HTML conversion is a
fallback for posts without raw content.

**Alternatives considered**:
- `markdownify`: Less popular, fewer users.
- Manual HTML parsing: Too complex, not worth implementing from scratch.

## Testing Framework

**Decision**: `pytest` (latest stable) + `pytest-cov`

**Rationale**: Standard in the Python ecosystem. Clean test discovery, fixture system, and
parametrize support. Required by constitution's TDD mandate. `pytest-cov` adds coverage
measurement and enforcement. Coverage threshold set to 80% minimum; build fails below it.

**Coverage configuration**: `pytest-cov` with `--cov=discourse_retrieval --cov-fail-under=80`
configured in `pyproject.toml` under `[tool.pytest.ini_options]`. Coverage report is
printed to stdout (`--cov-report=term-missing`) so developers see uncovered lines locally.

## Linting

**Decision**: `ruff` (latest stable)

**Rationale**: Single tool replacing flake8, isort, and pyupgrade. Fast, zero config for
reasonable defaults, and widely adopted. Satisfies the constitution's strict linting
requirement with minimal setup.

## Virtual Environment & Build Tooling

**Decision**: `uv` for virtual environment and dependency management; `Makefile` for
developer workflow automation.

**Rationale**: `uv` is fast (Rust-based), handles venv creation, dependency locking, and
package installation in one tool. It replaces the `python -m venv` + `pip install` workflow
with a single command (`uv sync`). It is widely adopted, actively maintained, and aligns
with the constitution's preference for reliable, popular tooling.

A `Makefile` exposes four standard targets (`build`, `lint`, `test`, `clean`) as the
single developer interface. This removes the need to remember tool-specific invocations
and provides a consistent entry point for both humans and CI.

**Alternatives considered**:
- `pip` + `venv` (stdlib): Works but slower and more verbose; no lockfile by default.
- `poetry`: Popular but heavier; `uv` covers the same use cases with less overhead.
- `hatch`: Good but less commonly used outside specific communities.

**Makefile targets**:

| Target | Command | Description |
|---|---|---|
| `build` | `uv sync` | Create/update venv and install all dependencies |
| `lint` | `uv run ruff check . && uv run ruff format --check .` | Run linter; non-zero exit on any warning |
| `test` | `uv run pytest` | Run tests with coverage; fails below 80% |
| `clean` | `rm -rf .venv dist *.egg-info .coverage` | Remove generated artifacts |

## Discourse API Approach

**Listing topics**: `GET /latest.json?order=created&ascending=false&page=N`

Returns up to 30 topics per page ordered by creation date descending. Pagination stops
when the oldest topic on a page predates `earliest_date`. Category filtering uses
`GET /c/{category_id}/l/latest.json?page=N` per configured category.

**Fetching full thread**: `GET /t/{id}.json?include_raw=1`

Returns all posts in the topic. `include_raw=1` includes the raw markdown source when
available, avoiding HTML conversion. The `posts_count` field in the response is stored
in the sidecar state file and used on re-runs to detect new replies.

**Authentication**: All requests include `Api-Key` and `Api-Username` headers. The
`Api-Username` defaults to `system` when not specified (read-only system user for
public-readable forums).

**Rate limiting**: Discourse returns HTTP 429 with a `Retry-After` header. The client
respects this header when present, otherwise uses exponential backoff starting at 1
second. Maximum retry attempts are controlled by `max_retries` in config (default: 5).

## State Tracking

**Decision**: Per-thread sidecar JSON file at `<output_dir>/YYYY/MM/<slug>.state.json`

Each state file contains:
```json
{
  "thread_id": 12345,
  "slug": "my-topic-title",
  "posts_count": 42,
  "downloaded_at": "2026-04-18T10:30:00Z"
}
```

On re-run, the tool checks whether a `.state.json` exists alongside the `.md` file. If it
does, it fetches just the topic metadata (lightweight) to compare `posts_count`. If
counts match, the thread is skipped. If the count has increased, the full thread is
re-downloaded and the state file updated.

**Why sidecar over single index**: Self-contained with content, survives partial cleanup
(delete a thread + its state to force re-download), and avoids a single file that grows
with archive size.
