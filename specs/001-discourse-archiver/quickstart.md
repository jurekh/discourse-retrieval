# Quickstart: Discourse Post Archiver

## Requirements

- Python 3.11+
- `uv` (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Discourse API key with read access to the forum

## Install & Build

```sh
git clone <repo>
cd discourse-retrieval
make build
```

`make build` runs `uv sync`, which creates a virtual environment under `.venv/` and
installs all runtime and dev dependencies from `uv.lock`.

## Developer Workflow

| Command | What it does |
|---|---|
| `make build` | Create/update venv, install all dependencies |
| `make lint` | Run ruff; exits non-zero on any warning |
| `make test` | Run tests with coverage; fails below 80% |
| `make clean` | Remove `.venv`, `dist`, `*.egg-info`, `.coverage` |

## Configure

Create a `config.toml` in your working directory:

```toml
forum_url = "https://forum.example.com"
api_key = "your-api-key-here"
output_dir = "./archive"
earliest_date = "2024-01-01"
```

Optionally restrict to specific categories (use Discourse category IDs):

```toml
categories = [4, 7]
```

Keep your API key out of config files by using an environment variable instead:

```sh
export DISCOURSE_API_KEY="your-api-key-here"
```

## Run

```sh
uv run discourse-retrieval
```

Or, if installed into the venv's PATH:

```sh
.venv/bin/discourse-retrieval
```

Output while running:

```
[2024/03] my-first-topic.md
[2024/03] another-topic.md
[2024/04] some-other-topic.md
Done. Downloaded: 3, Updated: 0, Skipped: 0
```

## Resume After Interruption

Press Ctrl-C at any time. Re-run the same command to resume:

```sh
uv run discourse-retrieval
```

Already-downloaded threads with no new replies are skipped automatically.
Threads with new replies since the last run are refreshed.

## Validate the Archive

```sh
ls archive/2024/03/
# my-first-topic.md   my-first-topic.state.json
# another-topic.md    another-topic.state.json

head archive/2024/03/my-first-topic.md
# # My First Topic
# **Category**: General
# **Created**: 2024-03-15
# ...
```

## Run Tests Manually

```sh
make test
```

Expected output includes a coverage summary:

```
---------- coverage: platform linux ----------
TOTAL     142    11    92%

===== N passed in 0.Xs =====
```

Build fails if total coverage drops below 80%.
