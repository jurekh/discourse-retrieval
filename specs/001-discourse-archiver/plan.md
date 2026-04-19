# Implementation Plan: Discourse Post Archiver

**Branch**: `001-discourse-archiver` | **Date**: 2026-04-19 | **Spec**: specs/001-discourse-archiver/spec.md  
**Input**: Feature specification from `specs/001-discourse-archiver/spec.md`

## Summary

A CLI tool that archives Discourse forum threads to local Markdown files under
`YYYY/MM/<slug>.md`. Reads config from `config.toml` (env overrides for API key),
downloads all threads since `earliest_date`, and supports Ctrl-C interrupt with
clean resume. Two-mode operation: backfill mode pages all historical content on
first run; incremental mode re-scans only recently active topics on subsequent runs
once backfill is complete.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: `requests` (HTTP client), `html2text` (HTML-to-Markdown)  
**Storage**: Local filesystem; TOML config via `tomllib` (stdlib); JSON state files  
**Testing**: `pytest` + `pytest-cov` (80% minimum coverage enforced)  
**Target Platform**: Linux / macOS CLI  
**Project Type**: CLI tool  
**Performance Goals**: Sequential downloads; throughput limited by Discourse API rate limits  
**Constraints**: Offline-safe atomic writes; no partial files on Ctrl-C  
**Scale/Scope**: Single-user tool; archives up to years of forum history

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Simplicity First | PASS | No framework overhead; stdlib used throughout |
| TDD (NON-NEGOTIABLE) | PASS | Tests written before implementation in all phases |
| Minimal Dependencies | PASS | Only 2 runtime deps (requests, html2text) |
| Strict Linting | PASS | ruff configured with E/W/F/I/UP/B/C4/RUF, line-length=99 |
| Incremental Git Workflow | PASS | Small commits per logical unit; no remote push |

## Project Structure

### Documentation (this feature)

```text
specs/001-discourse-archiver/
├── plan.md              # This file
├── research.md          # Technology and approach decisions
├── data-model.md        # Entities: Config, Thread, Post, DownloadState, ArchiveState
├── quickstart.md        # Integration scenarios
├── contracts/
│   ├── cli-interface.md
│   ├── config-schema.md
│   ├── state-schema.md        # Per-thread sidecar state
│   └── archive-state-schema.md  # Global archive state (new)
└── tasks.md
```

### Source Code (repository root)

```text
src/
└── discourse_retrieval/
    ├── __init__.py
    ├── cli.py          # argparse entry point; exit codes 0-3
    ├── config.py       # Config dataclass; from_file(); env overrides
    ├── client.py       # DiscourseClient; requests.Session; retry logic
    ├── archiver.py     # Archiver; run(); two-mode operation; signal handling
    ├── renderer.py     # ThreadRenderer; render(topic) -> str
    └── state.py        # DownloadState + ArchiveState dataclasses

tests/
├── unit/
│   ├── test_config.py
│   ├── test_state.py
│   ├── test_client.py
│   ├── test_renderer.py
│   ├── test_archiver.py
│   └── test_cli.py
└── integration/
    └── test_archiver.py
```

## Two-Mode Operation

### Backfill Mode

Condition: `archive.state.json` absent, or `backfill_complete = false`.

1. Paginate `/latest.json` (or `/c/{id}/l/latest.json` per category) from page 0.
2. For each topic with `created_at > oldest_topic_date` (if cursor present): fast-skip
   (no API call). These were already processed in a prior interrupted run.
3. For each topic at or past the cursor: check DownloadState sidecar; download or skip.
4. After each page is processed: update `oldest_topic_date` in `archive.state.json`
   atomically. This write survives interrupts and serves as the resume cursor.
5. Stop pagination when all topics on a page predate `earliest_date`.
6. On clean completion: write `backfill_complete = true` and `last_run = <now>`.

### Incremental Mode

Condition: `backfill_complete = true` in `archive.state.json`.

1. Paginate `/latest.json` sorted by last activity (Discourse default ordering).
2. For each topic: if `bumped_at < last_run`, stop pagination immediately.
3. For each topic in the activity window: apply the same DownloadState sidecar check.
4. On clean completion: update `last_run = <now>` in `archive.state.json`.

**Key invariants**:
- `oldest_topic_date` is written after every page - survives Ctrl-C, enables O(remaining)
  resume instead of O(all) re-pagination.
- `backfill_complete` and `last_run` are written only on clean completion, so incremental
  mode is never entered until a full backfill has succeeded.

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| `config.py` | Done | All fields, env overrides, validation |
| `state.py` (DownloadState) | Done | Save, load, needs_update, needs_download |
| `client.py` | Done | list_topics, list_category_topics, get_topic, get_topic_posts_count, retry |
| `renderer.py` | Done | render(), raw/cooked fallback, html2text |
| `archiver.py` | Done (backfill only) | Needs incremental mode + ArchiveState write |
| `cli.py` | Done | argparse, exit codes |
| `state.py` (ArchiveState) | Not started | New entity for global state |
| Incremental mode in archiver | Not started | FR-015 |
| `archive.state.json` write | Not started | FR-014 |

## Complexity Tracking

No constitution violations.
