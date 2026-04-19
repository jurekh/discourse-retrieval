# Contract: Archive State File Schema

## Location

```
<output_dir>/archive.state.json
```

One file per archive root. Tracks whether the full historical backfill is complete
and the timestamp of the last successful run.

## Schema

```json
{
  "backfill_complete": true,
  "last_run": "2026-04-19T10:00:00Z"
}
```

## Field Reference

| Field | Type | Description |
|---|---|---|
| `backfill_complete` | boolean | `true` once pagination has reached `earliest_date` without interruption. `false` if a prior run was interrupted during backfill. |
| `last_run` | string (ISO 8601 UTC) | Timestamp written at the end of the last clean (uninterrupted) run. Used as the activity cutoff in incremental mode. |

## Mode Selection Logic

```
if archive.state.json absent OR backfill_complete = false:
    MODE = backfill
    -> paginate all pages until earliest_date
else:  # backfill_complete = true
    MODE = incremental
    -> paginate until topic bumped_at < last_run, then stop
```

## Write Rules

1. The file MUST be written atomically (write to `.tmp`, then rename).
2. The file MUST only be written when a run completes without interruption.
3. A Ctrl-C interrupt MUST NOT update this file.
4. On clean completion:
   - Set `backfill_complete = true` (stays true once set).
   - Set `last_run = <current UTC timestamp>`.

## Relationship to Per-Thread State

`archive.state.json` controls **which pages to paginate** (macro-level).  
`<slug>.state.json` controls **whether to download each thread** (micro-level).  
Both must be consulted; the archive state avoids unnecessary page fetches,
while the per-thread state handles new-reply detection for threads in scope.
