# Data Model: Discourse Post Archiver

## Entities

### Config

Loaded from `config.toml` at startup. Environment variables override matching fields.

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `api_key` | string | yes | - | Discourse API key. Overridden by `DISCOURSE_API_KEY` env var. |
| `api_username` | string | no | `"system"` | Discourse API username. Overridden by `DISCOURSE_API_USERNAME` env var. |
| `forum_url` | string | yes | - | Base URL of the Discourse forum (e.g., `https://forum.example.com`). |
| `output_dir` | string | yes | - | Local directory to write archived files. Created if it does not exist. |
| `earliest_date` | date (YYYY-MM-DD) | yes | - | Only archive threads whose first post is on or after this date. |
| `categories` | list of integers | no | `[]` (all) | Discourse category IDs to archive. Empty means all accessible categories. |
| `max_retries` | integer | no | `5` | Maximum API retry attempts before aborting. |

**Validation rules**:
- `forum_url` MUST be a valid URL with scheme (`https://` or `http://`).
- `earliest_date` MUST be a valid ISO 8601 date.
- `max_retries` MUST be a positive integer.
- `api_key` MUST be non-empty after env override resolution.

---

### Thread

Represents a single Discourse topic fetched from the API. Not persisted directly; drives
the rendering of a markdown file.

| Field | Type | Description |
|---|---|---|
| `id` | integer | Discourse-assigned topic ID. |
| `slug` | string | Discourse-provided URL slug (e.g., `my-topic-title`). Used as filename base. |
| `title` | string | Display title of the thread. |
| `created_at` | datetime (UTC) | Timestamp of the first post. Determines YYYY/MM directory. |
| `posts_count` | integer | Total number of posts in the thread at time of fetch. |
| `category_id` | integer | Category this thread belongs to. |
| `posts` | list of Post | All posts in the thread, ordered by post number ascending. |

---

### Post

Represents a single message within a thread.

| Field | Type | Description |
|---|---|---|
| `id` | integer | Discourse-assigned post ID. |
| `post_number` | integer | Sequential position within the thread (1 = original post). |
| `author_name` | string | Display name of the post author. |
| `created_at` | datetime (UTC) | When this post was created. |
| `content` | string | Post body in Markdown. Sourced from raw content when available; otherwise converted from HTML. |

---

### DownloadState

Persisted as `<slug>.state.json` alongside the output markdown file.
Used to detect new replies and support resume-on-rerun.

| Field | Type | Description |
|---|---|---|
| `thread_id` | integer | Discourse topic ID. |
| `slug` | string | Discourse topic slug (matches filename). |
| `posts_count` | integer | Post count recorded at the time of last successful download. |
| `downloaded_at` | string (ISO 8601 UTC) | Timestamp of the last successful download. |

**State lifecycle**:
1. No state file + no markdown file: thread not yet downloaded -> download.
2. State file exists: compare `posts_count` against current API value.
   - Equal: skip (up to date).
   - Greater: re-download and overwrite both markdown and state files.
3. Markdown file exists but no state file: treat as incomplete -> re-download.

---

## Output File Structure

```text
<output_dir>/
  YYYY/
    MM/
      <slug>.md           # Thread content
      <slug>.state.json   # Download state sidecar
```

## Markdown File Format

Each thread is rendered as a single Markdown file:

```markdown
# <thread title>

**Category**: <category name>
**Created**: <ISO 8601 date>
**URL**: <canonical thread URL>

---

## Post 1 - <author display name> (<ISO 8601 datetime>)

<post body in markdown>

---

## Post 2 - <author display name> (<ISO 8601 datetime>)

<post body in markdown>

---
```
