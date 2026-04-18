# Implementation Plan: Discourse Post Archiver

**Branch**: `001-discourse-archiver` | **Date**: 2026-04-18 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-discourse-archiver/spec.md`

## Summary

Build a CLI tool that downloads Discourse forum threads to local Markdown files, organized
by YYYY/MM directories, with resume-on-rerun support via per-thread state sidecar files.
The tool uses the Discourse REST API with sequential fetching, exponential-backoff retries,
and re-downloads threads that have received new replies since the last run.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `requests` (HTTP), `html2text` (HTML->Markdown); `pytest`, `pytest-cov`, `ruff` (dev)
**Build Tooling**: `uv` (venv + dependency management); `Makefile` (build/lint/test/clean targets)
**Storage**: Local filesystem only; TOML config, JSON state files, Markdown output
**Testing**: `pytest` with `pytest-cov`; minimum 80% coverage enforced (build fails below threshold)
**Target Platform**: Linux / macOS
**Project Type**: CLI tool
**Performance Goals**: Not latency-sensitive; throughput bounded by Discourse API rate limits
**Constraints**: Sequential downloads only; max_retries configurable (default 5); clean Ctrl-C exit within 5s
**Scale/Scope**: Single-user archival tool; no concurrency requirement

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Simplicity First | PASS | Sequential design, no concurrency, minimal abstraction layers |
| II. TDD (NON-NEGOTIABLE) | PASS | All tasks structured tests-first; failing tests precede implementation |
| III. Minimal Dependencies | PASS | 2 runtime deps (requests, html2text); 3 dev deps (pytest, pytest-cov, ruff); stdlib covers rest |
| IV. Strict Linting | PASS | ruff configured; zero-warning policy enforced in CI |
| V. Incremental Git Workflow | PASS | Tasks structured as small logical units; each task = one commit |

No violations. No complexity justification required.

## Project Structure

### Documentation (this feature)

```text
specs/001-discourse-archiver/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── cli-interface.md
│   ├── config-schema.md
│   └── state-schema.md
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Source Code (repository root)

```text
src/
  discourse_retrieval/
    __init__.py
    cli.py          # entry point, argument parsing, signal handling
    config.py       # config.toml loading, env override, validation
    client.py       # Discourse API client (requests session, pagination, retry)
    archiver.py     # download orchestration, resume logic, progress output
    renderer.py     # Thread -> Markdown rendering
    state.py        # DownloadState read/write (sidecar JSON)

tests/
  unit/
    test_config.py
    test_renderer.py
    test_state.py
    test_client.py
  integration/
    test_archiver.py

Makefile            # build/lint/test/clean targets (uv-based)
pyproject.toml      # project metadata, dependencies, ruff config, pytest+coverage config
uv.lock             # generated lockfile (committed)
```

**Structure Decision**: Single project. CLI entry point installed via `pyproject.toml`
`[project.scripts]`. Source under `src/` layout for clean import isolation.

## Complexity Tracking

> No constitution violations to justify.
