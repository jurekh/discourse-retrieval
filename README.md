# discourse-retrieval

CLI tool that archives Discourse forum threads to local markdown files.

Each thread is written to `<output_dir>/YYYY/MM/<thread-slug>.md` based on the
date of the first post. State is tracked in `<output_dir>/archive.state.json`
so interrupted runs resume where they left off.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (package manager)

## Installation

```bash
git clone <repo-url>
cd <cloned-dir>
make build
```

This installs the tool and its dependencies into a local `.venv`.

## Configuration

Copy the sample config and edit it:

```bash
cp config.toml.sample config.toml
```

`config.toml` fields:

| Field | Required | Description |
|---|---|---|
| `forum_url` | yes | Discourse forum URL, no trailing slash (e.g. `https://forum.example.com`) |
| `api_key` | no* | Discourse API key. Can be set via `DISCOURSE_API_KEY` env var instead |
| `api_username` | no* | API username. Can be set via `DISCOURSE_API_USERNAME` env var. Default: `system` |
| `earliest_date` | yes | Oldest thread date to retrieve on first run, `YYYY-MM-DD` |
| `output_dir` | yes | Directory to write files into |
| `categories` | no | List of category IDs to archive. Omit to archive all categories |
| `max_retries` | no | Retry attempts on HTTP 429 rate limiting. Default: `5` |

*`api_key` is required either in the config file or via the environment variable.

### Getting an API key

In Discourse: **Admin > API > New API Key**. A key scoped to read-only with
username `system` is sufficient.

### Using environment variables

```bash
export DISCOURSE_API_KEY="your-api-key"
export DISCOURSE_API_USERNAME="system"
```

Environment variables take precedence over values in the config file.

## Running

```bash
uv run discourse-archive
```

This reads `./config.toml` by default. To specify a different config file:

```bash
uv run discourse-archive /path/to/config.toml
```

### First run

The first run performs a full backfill from `earliest_date` to today, fetching
threads newest-first. Progress is written to disk after each thread. Expect many
API pages for large forums.

### Interrupting and resuming

Press `Ctrl-C` to stop. The cursor (`oldest_topic_date` in `archive.state.json`)
is updated after each thread, so re-running resumes from where it stopped.
Already-archived threads that have not changed are skipped without re-fetching.

### Subsequent runs

Once the backfill is complete, re-running fetches only threads that have had new
activity since the last completed run.

## Output format

Each thread file looks like:

```
# Thread Title

**Category**: General
**Created**: 2024-03-15
**URL**: <topic-url>/thread-slug/42

---

## Post 1 - Alice Smith (2024-03-15 10:00:00Z)

First post body

---

## Post 2 - Bob Jones (2024-03-15 11:30:00Z)

Reply body

---
```

## Development

```bash
make build      # install dependencies
make test       # pytest with coverage (80% minimum enforced)
make lint       # ruff check + format check
make clean      # remove .venv and build artifacts
```
