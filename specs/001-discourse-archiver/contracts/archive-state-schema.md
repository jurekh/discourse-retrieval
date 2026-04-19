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
  "last_run": "2026-04-19T10:00:00Z",
  "oldest_topic_date": "2024-01-03T08:15:00Z"
}
```

## Field Reference

| Field | Type | Description |
|---|---|---|
| `backfill_complete` | boolean | `true` once pagination has reached `earliest_date` on a clean run. `false` if a prior run was interrupted during backfill. |
| `last_run` | string (ISO 8601 UTC) | Timestamp of the last clean (uninterrupted) run. Used as the activity cutoff in incremental mode. `null` if no clean run has completed yet. |
| `oldest_topic_date` | string (ISO 8601 UTC) | Cursor: the `created_at` of the oldest topic successfully processed in the current backfill. Updated after each page. Absent on first run. |

## Mode Selection Logic

```
if archive.state.json absent OR backfill_complete = false:
    MODE = backfill
    -> paginate pages from 0 toward earliest_date
    -> skip topics with created_at > oldest_topic_date (already processed)
    -> download or check topics with created_at <= oldest_topic_date (new territory)
else:  # backfill_complete = true
    MODE = incremental
    -> paginate until topic bumped_at < last_run, then stop
```

## Write Rules

1. The file MUST be written atomically (write to `.tmp`, then rename).
2. During backfill: update `oldest_topic_date` after each page is successfully processed.
   This write MUST happen even on an interrupted run (it is the resume cursor).
3. On clean completion of backfill:
   - Set `backfill_complete = true` (stays true once set).
   - Set `last_run = <current UTC timestamp>`.
4. On clean completion of an incremental run:
   - Update `last_run = <current UTC timestamp>`.
5. A Ctrl-C interrupt MUST NOT prevent the most recent per-page `oldest_topic_date`
   update from being written; only `backfill_complete` and `last_run` require a clean run.

## Resume Behaviour on Interrupted Backfill

Given `oldest_topic_date = T` from a prior interrupted run:

1. Paginate from page 0 as normal.
2. For each topic with `created_at > T`: fast-skip (no API call, no sidecar check).
   These were already paginated and downloaded in the prior run.
3. When the first topic with `created_at <= T` is encountered: switch to normal
   download logic (check per-thread sidecar, download if needed).
4. Continue until all remaining pages reach `earliest_date`.
5. On clean completion: write `backfill_complete = true` and `last_run`.

This makes interrupted backfill resume O(remaining_topics) rather than O(all_topics).

## Relationship to Per-Thread State

`archive.state.json` controls **which pages to paginate and where to resume**
(macro-level).  
`<slug>.state.json` controls **whether to download each thread** (micro-level).  
Both must be consulted; the archive state avoids re-checking already-processed
pages, while the per-thread state handles new-reply detection for in-scope threads.
