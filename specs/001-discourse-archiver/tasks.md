---
description: "Task list for Discourse Post Archiver implementation"
---

# Tasks: Discourse Post Archiver

**Input**: Design documents from `specs/001-discourse-archiver/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**TDD**: Tests are MANDATORY per project constitution (Principle II: NON-NEGOTIABLE).
All test tasks MUST be written and confirmed failing before their implementation tasks begin.

**Organization**: Tasks are grouped by user story to enable independent implementation
and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in all task descriptions

---

## Phase 1: Setup

**Purpose**: Project initialization. No user story work begins until this phase is complete.

- [x] T001 Create `pyproject.toml` with project metadata (`name = "discourse-retrieval"`, `requires-python = ">=3.11"`), runtime deps (`requests`, `html2text`), dev deps (`pytest`, `pytest-cov`, `ruff`), `[project.scripts]` entry point (`discourse-retrieval = "discourse_retrieval.cli:main"`), `[tool.ruff]` config (strict rules), and `[tool.pytest.ini_options]` with `addopts = "--cov=discourse_retrieval --cov-report=term-missing --cov-fail-under=80"`
- [x] T002 [P] Create `Makefile` with targets: `build` (`uv sync`), `lint` (`uv run ruff check . && uv run ruff format --check .`), `test` (`uv run pytest`), `clean` (`rm -rf .venv dist *.egg-info .coverage .pytest_cache`)
- [x] T003 [P] Create `src/discourse_retrieval/__init__.py` (empty, marks package)
- [x] T004 [P] Create `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`
- [x] T005 Run `make build` to create `.venv` and generate `uv.lock`; commit `uv.lock`

**Checkpoint**: `make build` succeeds, `make lint` and `make test` run (zero tests pass is OK at this stage)

---

## Phase 2: Foundational

**Purpose**: Config loading, API client, and state management. All user stories depend on these.

**NOTE**: Write each test file, run it to confirm it fails, then implement.

### Tests for Config (write first, confirm failing)

- [x] T006 [P] Write failing tests for `Config` in `tests/unit/test_config.py`: test TOML loading of all fields, `DISCOURSE_API_KEY` env override, `DISCOURSE_API_USERNAME` env override, validation errors for missing `forum_url`/`api_key`/`output_dir`/`earliest_date`, invalid `forum_url` (no scheme), invalid `earliest_date` format, invalid `max_retries` (zero/negative), and `categories` as empty list default

### Implementation: Config

- [x] T007 Implement `Config` dataclass in `src/discourse_retrieval/config.py`: load `config.toml` via `tomllib`, apply env overrides (`DISCOURSE_API_KEY`, `DISCOURSE_API_USERNAME`), validate all fields, raise `ValueError` with the message format from `contracts/config-schema.md`, expose `from_file(path: Path) -> Config` classmethod

### Tests for DownloadState (write first, confirm failing)

- [x] T008 [P] Write failing tests for `DownloadState` in `tests/unit/test_state.py`: test `save()` writes correct JSON to `<slug>.state.json` alongside the `.md` file, `load()` reads it back, `load()` returns `None` when file absent, `needs_update(current_posts_count)` returns `False` when counts match and `True` when current count is higher

### Implementation: DownloadState

- [x] T009 Implement `DownloadState` dataclass in `src/discourse_retrieval/state.py`: fields `thread_id`, `slug`, `posts_count`, `downloaded_at`; `save(md_path: Path)` writes sidecar JSON; `load(md_path: Path) -> DownloadState | None` reads it; `needs_update(current: int) -> bool` compares post counts

### Tests for DiscourseClient (write first, confirm failing)

- [x] T010 [P] Write failing tests for `DiscourseClient` in `tests/unit/test_client.py`: use `unittest.mock.patch` to mock `requests.Session.get`; test auth headers (`Api-Key`, `Api-Username`) present on every request; test `list_topics(page)` parses topic list response and returns list of topic dicts; test `get_topic(id)` returns full topic dict; test `get_topic_posts_count(id)` returns integer; test retry on HTTP 429 with `Retry-After` header; test retry exhaustion raises exception after `max_retries` attempts; test exponential backoff delays (mock `time.sleep`)

### Implementation: DiscourseClient

- [x] T011 Implement `DiscourseClient` in `src/discourse_retrieval/client.py`: `__init__(config: Config)` sets up `requests.Session` with `Api-Key` and `Api-Username` headers and `timeout=30`; `list_topics(page: int) -> list[dict]` calls `GET /latest.json?order=created&ascending=false&page={page}`; `list_category_topics(category_id: int, page: int) -> list[dict]` calls `GET /c/{category_id}/l/latest.json?page={page}`; `get_topic(topic_id: int) -> dict` calls `GET /t/{topic_id}.json?include_raw=1`; `get_topic_posts_count(topic_id: int) -> int` calls `GET /t/{topic_id}.json` and returns `posts_count` field; internal `_request_with_retry(method, url, **kwargs)` implements exponential backoff respecting `Retry-After` header, raises `RuntimeError` after `max_retries` exhausted

**Checkpoint**: Foundation ready - `make test` passes all unit tests for config, state, and client

---

## Phase 3: User Story 1 - Initial Archive Download (Priority: P1)

**Goal**: Download all threads from the configured forum since `earliest_date` and write
them as markdown files under `output_dir/YYYY/MM/<slug>.md`.

**Independent Test**: Run `discourse-retrieval --config config.toml` against a real or
mocked forum; verify markdown files appear under correct YYYY/MM paths with all posts.

### Tests for ThreadRenderer (write first, confirm failing)

- [x] T012 [P] [US1] Write failing tests for `ThreadRenderer` in `tests/unit/test_renderer.py`: test `render(topic_dict) -> str` produces a string starting with `# <title>`; test metadata block contains `**Category**`, `**Created**`, `**URL**`; test each post renders as `## Post N - <author> (<datetime>)` followed by content; test raw content is used when `raw` field present; test `html2text` conversion applied when only `cooked` HTML field present; test post separator `---` between posts

### Implementation: ThreadRenderer

- [x] T013 [P] [US1] Implement `ThreadRenderer` in `src/discourse_retrieval/renderer.py`: `render(topic: dict) -> str` builds complete markdown string; extract title, category name, created_at, thread URL from topic dict; iterate `post_stream.posts`; use `raw` field if non-empty, else convert `cooked` HTML via `html2text.html2text()`; format each post with author display name and ISO 8601 datetime

### Integration test for US1 (write first, confirm failing)

- [x] T014 [US1] Write failing integration test in `tests/integration/test_archiver.py`: mock `DiscourseClient` to return two topics (one matching `earliest_date` filter, one older); call `Archiver(config).run()`; assert two markdown files exist at correct `YYYY/MM/<slug>.md` paths; assert two `.state.json` files exist alongside them; assert progress lines printed to stdout; assert final summary line printed

### Implementation: Archiver download loop

- [x] T015 [US1] Implement `Archiver` class in `src/discourse_retrieval/archiver.py`: `__init__(config: Config)` stores config, creates `DiscourseClient` and `ThreadRenderer`; `_output_path(topic: dict) -> Path` returns `Path(config.output_dir) / YYYY / MM / f"{slug}.md"` derived from topic `created_at`; `_download_thread(topic: dict)` fetches full topic, renders markdown, writes `.md` file (creates parent dirs), writes `.state.json` sidecar, prints `[YYYY/MM] {slug}.md` to stdout; `run()` paginates topic list, filters topics with `created_at >= config.earliest_date`, calls `_download_thread()` for each, prints summary line on completion

### Implementation: CLI entry point

- [x] T016 [US1] Implement `main()` in `src/discourse_retrieval/cli.py`: `argparse.ArgumentParser` with `--config` (default `./config.toml`) and `--version` flags; load `Config.from_file(path)`; instantiate and call `Archiver(config).run()`; exit code 1 on `ValueError` (config error), exit code 2 on `RuntimeError` (API error), exit code 3 on `OSError` (filesystem error); print error messages to stderr in format `error: <message>`

**Checkpoint**: `make test` passes; `uv run discourse-retrieval --config config.toml` downloads
threads and writes markdown files to `output_dir/YYYY/MM/<slug>.md`

---

## Phase 4: User Story 2 - Interrupt and Resume (Priority: P2)

**Goal**: Ctrl-C exits cleanly without corrupting files; re-run skips up-to-date threads
and re-downloads threads with new replies.

**Independent Test**: Run, interrupt with Ctrl-C, re-run; verify skipped count equals
already-downloaded count and updated count reflects threads with new replies.

### Tests for resume logic (write first, confirm failing)

- [x] T017 [P] [US2] Write failing unit tests for resume logic in `tests/unit/test_state.py` (extend existing file): test that `DownloadState.needs_update(42)` returns `False` when `posts_count == 42`; test returns `True` when `posts_count == 40` and current is 42; test that absent state file + absent md file -> `needs_download` helper returns `True`; test absent state file + present md file -> `needs_download` returns `True` (treat as incomplete)

- [x] T018 [P] [US2] Write failing unit tests for interrupt handling in `tests/unit/test_archiver.py` (new file): mock `signal.signal` and verify `SIGINT` handler is registered in `Archiver.run()`; test that when the interrupt flag is set mid-loop, the loop exits cleanly and prints the interrupted summary line `"Interrupted. Downloaded: N, Updated: N, Skipped: N (resumable)"`

### Implementation: resume and interrupt

- [x] T019 [US2] Add resume logic to `Archiver._should_download(topic: dict) -> tuple[bool, bool]` in `src/discourse_retrieval/archiver.py`: returns `(should_download, is_update)`; if no `.md` or no `.state.json` -> `(True, False)`; if both exist, fetch `posts_count` via `client.get_topic_posts_count()` and compare to state; return `(True, True)` if update needed, `(False, False)` if up to date; wire into `run()` loop: skip if `(False, False)`, increment `skipped` counter; increment `updated` counter on updates

- [x] T020 [US2] Add `SIGINT` handler to `Archiver.run()` in `src/discourse_retrieval/archiver.py`: register `signal.signal(signal.SIGINT, handler)` before loop; handler sets `self._interrupted = True`; loop checks flag after each thread and exits cleanly; on interrupt, print `"Interrupted. Downloaded: N, Updated: N, Skipped: N (resumable)"` to stdout; ensure partially-written `.md` file is removed if write was in progress (use temp file + atomic rename pattern)

**Checkpoint**: Run tool, press Ctrl-C, re-run; second run shows `Downloaded: 0, Updated: 0, Skipped: N`
for all previously complete threads. `make test` passes.

---

## Phase 5: User Story 3 - Category/Filter Selection (Priority: P3)

**Goal**: When `categories` is set in config, only threads from those categories are downloaded.

**Independent Test**: Configure one category ID; run tool; verify output contains only
threads from that category.

### Tests for category filtering (write first, confirm failing)

- [x] T021 [P] [US3] Write failing unit tests for category filtering in `tests/unit/test_client.py` (extend existing file): test `DiscourseClient.list_category_topics(category_id=4, page=0)` calls the correct endpoint `GET /c/4/l/latest.json?page=0`; test that when config has `categories = [4, 7]`, `Archiver` calls `list_category_topics` for each configured category instead of `list_topics`

### Implementation: category filtering

- [x] T022 [US3] Wire `config.categories` into `Archiver.run()` in `src/discourse_retrieval/archiver.py`: if `config.categories` is non-empty, iterate over each category ID and call `client.list_category_topics(cat_id, page)` per category; deduplicate topics by `id` in case a topic appears in multiple configured categories; if `config.categories` is empty, use existing `client.list_topics(page)` path

**Checkpoint**: Set `categories = [N]` in config, run tool; only threads from that category
appear in output. `make test` passes. All three user stories independently testable.

---

## Phase N: Polish and Cross-Cutting Concerns

**Purpose**: Coverage enforcement, linting, and final validation.

- [x] T023 Run `make test` and check coverage report; add unit tests in `tests/unit/` for any module below 80% coverage (focus on error paths: missing config fields, OSError on write, empty topic list, pagination stop condition)
- [x] T024 [P] Run `make lint`; fix any ruff warnings across all source and test files
- [x] T025 [P] Validate `quickstart.md` steps: run `make build`, create a `config.toml` pointing at a test forum or mock server, run `uv run discourse-retrieval`, confirm output matches documented format
- [x] T026 Verify atomic write pattern in `Archiver._download_thread()`: confirm that a simulated write failure (mock `OSError` mid-write) leaves no partial `.md` file and no `.state.json` at that path

---

## Phase 6: Archive State and Incremental Mode (US2 extension)

**Purpose**: Implement `ArchiveState` (FR-014) and two-mode operation (FR-015): backfill
mode with per-page cursor writes for interrupt-safe resume; incremental mode that only
re-examines topics with activity since the last clean run.

**Independent Test**: Run tool to completion, verify `archive.state.json` contains
`backfill_complete=true`. Interrupt a second run mid-backfill, verify `oldest_topic_date`
updated but `backfill_complete` unchanged. Re-run, verify cursor topics fast-skipped.

### Tests for ArchiveState (write first, confirm failing)

- [ ] T027 [P] [US2] Write failing unit tests for `ArchiveState` in `tests/unit/test_state.py` (extend existing file): test `save(output_dir)` writes `archive.state.json` in `output_dir`; test `load(output_dir)` reads it back; test `load()` returns `None` when absent; test `update_cursor(date_str)` sets `oldest_topic_date` and keeps the minimum across calls without changing `backfill_complete` or `last_run`; test `mark_complete(now)` sets `backfill_complete=True` and `last_run`

### Implementation: ArchiveState

- [ ] T028 [US2] Add `ArchiveState` dataclass to `src/discourse_retrieval/state.py`: fields `backfill_complete: bool = False`, `last_run: str | None = None`, `oldest_topic_date: str | None = None`; `save(output_dir: Path)` atomic write (tmp + rename) to `output_dir/archive.state.json`; `load(output_dir: Path) -> ArchiveState | None`; `update_cursor(topic_date: str)` sets field to minimum of current and given ISO8601 date string; `mark_complete(now: str)` sets `backfill_complete=True` and `last_run=now`

### Tests for activity-ordered listing (write first, confirm failing)

- [ ] T029 [P] [US2] Write failing unit tests for activity-sorted listing in `tests/unit/test_client.py` (extend existing file): test `list_topics(page=0, order='activity')` calls `GET /latest.json` without `order` or `ascending` params; test `list_topics(page=0)` (default) still sends `order=created&ascending=false` (no regression); same for `list_category_topics` variants

### Implementation: client order parameter

- [ ] T030 [P] [US2] Add `order` parameter to `DiscourseClient.list_topics()` and `list_category_topics()` in `src/discourse_retrieval/client.py`: `order: str = 'created'`; when `order='created'` include `order=created&ascending=false` params (existing behaviour); when `order='activity'` omit those params (Discourse default ordering by `bumped_at`)

### Tests for two-mode archiver (write first, confirm failing)

- [ ] T031 [US2] Write failing integration tests for archive state and modes in `tests/integration/test_archiver.py` (extend existing file): test clean run writes `archive.state.json` with `backfill_complete=True` and `last_run` set; test run interrupted before any download (`_interrupted=True`) does NOT set `backfill_complete=True`; test that after one page of topics is processed an interrupted run has `oldest_topic_date` set; test resume from cursor skips topics newer than `oldest_topic_date` without calling `get_topic_posts_count`; test incremental mode (`backfill_complete=True` preset) stops pagination when `bumped_at < last_run` and does not call `get_topic` for topics outside the window

### Implementation: two-mode Archiver

- [ ] T032 [US2] Modify `Archiver.run()` in `src/discourse_retrieval/archiver.py`: load `ArchiveState.load(config.output_dir)` at startup; pass archive state to `_iter_topics()`; after each page in backfill mode call `archive_state.update_cursor(oldest_created_at_on_page)` and save atomically; on clean completion (no interrupt) call `archive_state.mark_complete(now)` and save

- [ ] T033 [US2] Modify `Archiver._iter_topics()` and `_paginate()` in `src/discourse_retrieval/archiver.py`: in backfill mode fast-skip (no yield, no sidecar check) topics with `created_at > oldest_topic_date`; in incremental mode pass `order='activity'` to listing calls and stop pagination when any topic's `bumped_at < last_run`

**Checkpoint**: `make test` passes. Interrupt a run, re-run; confirm topics newer than cursor produce no `get_topic_posts_count` calls. On a completed run, confirm second run uses activity ordering and stops early.

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational completion
- **US2 (Phase 4)**: Depends on US1 completion (extends `Archiver` class built in US1)
- **US3 (Phase 5)**: Depends on Foundational completion (can run after Phase 2, parallel with US1/US2 if staffed)
- **Polish (Phase N)**: Depends on all desired user stories complete
- **Archive State (Phase 6)**: Depends on Phase 4 (US2) and Phase N; extends existing Archiver

### User Story Dependencies

- **US1 (P1)**: After Foundational - no dependency on US2/US3
- **US2 (P2)**: After US1 - extends `Archiver` class; independently testable after US1
- **US3 (P3)**: After Foundational - independently testable; no dependency on US1/US2

### TDD Order Within Each Phase

For each module: write test -> confirm test fails -> implement -> confirm test passes

---

## Parallel Opportunities

### Phase 2 (Foundational)

```
Parallel batch 1 (write tests):
  T006  Write test_config.py
  T008  Write test_state.py
  T010  Write test_client.py

Sequential (implement after tests confirmed failing):
  T007  Implement config.py       (after T006 confirmed failing)
  T009  Implement state.py        (after T008 confirmed failing)
  T011  Implement client.py       (after T010 confirmed failing)
```

### Phase 3 (US1)

```
Parallel batch 1 (write tests):
  T012  Write test_renderer.py
  T014  Write integration test (archiver)

Parallel batch 2 (implement after tests failing):
  T013  Implement renderer.py
  T015  Implement archiver.py     (after T014 failing)

Sequential:
  T016  Implement cli.py          (after T015 complete)
```

### Phase 6 (Archive State + Incremental Mode)

```
Parallel batch 1 (write tests):
  T027  Write ArchiveState unit tests
  T029  Write activity-sort client tests

Parallel batch 2 (implement after tests failing):
  T028  Implement ArchiveState in state.py
  T030  Add order param to client.py

Sequential (depends on T028 + T030):
  T031  Write integration tests for two-mode archiver
  T032  Modify Archiver.run() for ArchiveState
  T033  Modify _iter_topics()/_paginate() for cursor + incremental mode
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. **STOP and VALIDATE**: `uv run discourse-retrieval` downloads threads correctly
5. `make test` passes, `make lint` clean

### Incremental Delivery

1. Setup + Foundational -> foundation ready
2. US1 -> basic archiver works, independently testable
3. US2 -> interruption safe, resume works
4. US3 -> category filtering works
5. Polish -> 80% coverage enforced, lint clean

---

## Notes

- `[P]` tasks within the same phase touch different files and have no inter-dependencies
- TDD is non-negotiable per constitution: tests written, confirmed failing, then implemented
- Commit after each completed task (or small logical group) with a message explaining what and why
- Do NOT push commits to remote
- Atomic write pattern for `.md` files: write to `<slug>.md.tmp`, rename to `<slug>.md` on success
- Each user story phase ends with a checkpoint that verifies the story is independently functional
