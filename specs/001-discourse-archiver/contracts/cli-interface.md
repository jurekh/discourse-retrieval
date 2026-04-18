# Contract: CLI Interface

## Command

```
discourse-retrieval [OPTIONS]
```

## Options

| Flag | Type | Default | Description |
|---|---|---|---|
| `--config PATH` | path | `./config.toml` | Path to config.toml file. |
| `--help` | flag | - | Print usage and exit. |
| `--version` | flag | - | Print version and exit. |

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Completed successfully (including clean Ctrl-C interrupt). |
| 1 | Configuration error (missing required field, invalid value). |
| 2 | API error after retries exhausted. |
| 3 | Filesystem error (cannot create output directory, write failure). |

## Standard Output (stdout)

One line per downloaded or updated thread:

```
[YYYY/MM] <slug>.md
```

Final summary line on completion:

```
Done. Downloaded: N, Updated: N, Skipped: N
```

On Ctrl-C interrupt:

```
Interrupted. Downloaded: N, Updated: N, Skipped: N (resumable)
```

## Standard Error (stderr)

Error messages only. Format:

```
error: <human-readable description>
```

Examples:
```
error: config field 'forum_url' is required
error: API request failed after 5 retries: 429 Too Many Requests
error: cannot write to output directory '/tmp/out': Permission denied
```

## Environment Variables

| Variable | Overrides | Description |
|---|---|---|
| `DISCOURSE_API_KEY` | `api_key` in config.toml | Discourse API key. Takes precedence when set and non-empty. |
| `DISCOURSE_API_USERNAME` | `api_username` in config.toml | Discourse API username. Takes precedence when set and non-empty. |
