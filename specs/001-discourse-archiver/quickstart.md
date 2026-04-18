# Quickstart: Discourse Post Archiver

## Requirements

- Python 3.11+
- A Discourse API key with read access to the forum

## Install

```sh
pip install discourse-retrieval
```

Or from source:

```sh
git clone <repo>
cd discourse-retrieval
pip install -e .
```

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
discourse-retrieval
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
discourse-retrieval
```

Already-downloaded threads with no new replies are skipped automatically.
Threads with new replies since the last run are refreshed.

## Validation

Verify the archive looks correct:

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
