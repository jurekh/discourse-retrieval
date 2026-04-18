# Contract: State File Schema

## Location

```
<output_dir>/YYYY/MM/<slug>.state.json
```

One state file per downloaded thread, stored alongside the corresponding `.md` file.

## Schema

```json
{
  "thread_id": 12345,
  "slug": "my-topic-title",
  "posts_count": 42,
  "downloaded_at": "2026-04-18T10:30:00Z"
}
```

## Field Reference

| Field | Type | Description |
|---|---|---|
| `thread_id` | integer | Discourse topic ID. |
| `slug` | string | Discourse topic slug (matches the `.md` filename without extension). |
| `posts_count` | integer | Post count recorded at last successful download. Used to detect new replies. |
| `downloaded_at` | string | ISO 8601 UTC timestamp of last successful download. |

## Resume Logic

On re-run the tool applies this decision for each thread in scope:

1. No `.state.json` and no `.md` file -> download.
2. `.md` file exists but no `.state.json` -> treat as incomplete, re-download.
3. Both `.state.json` and `.md` file exist:
   a. Fetch current `posts_count` from Discourse topic metadata (lightweight HEAD-level request).
   b. If `posts_count` matches state file -> skip.
   c. If Discourse `posts_count` > state file value -> re-download and overwrite both files.
