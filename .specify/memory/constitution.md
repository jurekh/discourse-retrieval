<!--
SYNC IMPACT REPORT
==================
Version change: [template] -> 1.0.0
Modified principles: N/A (initial ratification)
Added sections:
  - Core Principles (I-V)
  - Code Quality Standards
  - Development Workflow
  - Governance
Removed sections: N/A
Templates requiring updates:
  - .specify/templates/plan-template.md: Constitution Check gates align with principles below [OK - gates are principle-derived]
  - .specify/templates/spec-template.md: No mandatory section changes required [OK]
  - .specify/templates/tasks-template.md: TDD task ordering (tests-first) already present [OK]
Follow-up TODOs: None
-->

# Discourse Retrieval Constitution

## Core Principles

### I. Simplicity First

Every design MUST use the simplest solution that satisfies requirements.
YAGNI (You Aren't Gonna Need It) applies at every level: no speculative abstractions,
no future-proofing patterns, no premature generalization.
Complexity MUST be justified in writing before introduction.
Three similar lines of code is preferred over a premature abstraction.

Rationale: Simple code is easier to review, debug, and maintain. Complexity compounds risk.

### II. Test-Driven Development (NON-NEGOTIABLE)

All production code MUST be preceded by a failing test.
Red-Green-Refactor is the only permitted implementation cycle.
Tests MUST be written and confirmed failing before any implementation begins.
User story acceptance scenarios MUST map 1:1 to automated tests.

Rationale: Tests written after implementation verify current behavior, not requirements.
TDD forces clarity on expected behavior before coding decisions are made.

### III. Minimal External Dependencies

Standard library solutions MUST be used unless an external dependency provides
a material, non-trivial advantage. When an external dependency is necessary,
it MUST be widely adopted, actively maintained, and have a stable release history.
Each new dependency requires explicit justification documenting why the standard
library is insufficient.

Rationale: Each dependency is a maintenance liability, a security surface, and a
compatibility risk. Prefer boring, proven choices over novel ones.

### IV. Strict Linting

All code MUST pass linter checks with zero warnings before commit.
Linter configuration MUST be checked into the repository.
Linter rules MUST NOT be suppressed with inline comments except to work around
a documented upstream bug, with a link to that bug in the suppression comment.

Rationale: Consistent style removes cognitive overhead during review. Linting catches
real bugs (unused vars, shadowed names, type mismatches) beyond style enforcement.

### V. Incremental Git Workflow

Every logical unit of work MUST be committed independently with a message that
explains what was done and why (not just what).
Commits MUST NOT be pushed to the remote repository during development.
Each commit MUST leave the codebase in a passing state (tests green, linter clean).

Rationale: Small commits make review tractable and git history useful as documentation.
No-push policy keeps work local until explicitly reviewed and approved.

## Code Quality Standards

- Code MUST be self-documenting through accurate naming; comments are reserved for
  non-obvious invariants, hidden constraints, or workarounds for specific bugs.
- Functions and methods MUST have a single, clear responsibility.
- Error handling MUST be explicit; silent failures are not permitted.
- Magic numbers and strings MUST be named constants.
- Dead code MUST be deleted, not commented out.

## Development Workflow

- Tests are written first; implementation follows only after tests are confirmed failing.
- Each feature branch starts from a clean main.
- Pull requests MUST include a description of what changed and why.
- Code review MUST verify constitution compliance before merge.
- All tests MUST pass and linting MUST be clean before a PR is opened.
- Dependencies added during a feature MUST be documented with justification in the PR.

## Governance

This constitution supersedes all informal conventions and per-feature agreements.
Amendments require:
1. A written proposal documenting the motivation.
2. Version bump per semantic versioning rules (see below).
3. Update to `LAST_AMENDED_DATE`.
4. Propagation check across all `.specify/templates/` files.

Versioning policy:
- MAJOR: Backward-incompatible governance change or principle removal/redefinition.
- MINOR: New principle or section added, or material expansion of existing guidance.
- PATCH: Clarification, wording fix, or non-semantic refinement.

All PRs and reviews MUST verify compliance with the principles above.
Violations MUST be documented in the Complexity Tracking table in plan.md with justification.

**Version**: 1.0.0 | **Ratified**: 2026-04-18 | **Last Amended**: 2026-04-18
