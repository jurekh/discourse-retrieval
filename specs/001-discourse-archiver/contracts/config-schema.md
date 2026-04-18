# Contract: config.toml Schema

## Minimal Example

```toml
forum_url = "https://forum.example.com"
api_key = "your-api-key-here"
output_dir = "/path/to/archive"
earliest_date = "2024-01-01"
```

## Full Example

```toml
forum_url = "https://forum.example.com"
api_key = "your-api-key-here"
api_username = "system"
output_dir = "/path/to/archive"
earliest_date = "2024-01-01"
categories = [4, 7, 12]
max_retries = 5
```

## Field Reference

| Field | TOML Type | Required | Default | Validation |
|---|---|---|---|---|
| `forum_url` | string | yes | - | Valid URL with scheme |
| `api_key` | string | yes* | - | Non-empty. Overridden by `DISCOURSE_API_KEY` env var. |
| `api_username` | string | no | `"system"` | Non-empty string if provided. Overridden by `DISCOURSE_API_USERNAME`. |
| `output_dir` | string | yes | - | Valid filesystem path (need not exist yet) |
| `earliest_date` | string | yes | - | ISO 8601 date: `YYYY-MM-DD` |
| `categories` | array of integers | no | `[]` | Each value must be a positive integer |
| `max_retries` | integer | no | `5` | Must be >= 1 |

*`api_key` can be omitted from config.toml if `DISCOURSE_API_KEY` is set in the environment.

## Env Override Rules

1. `DISCOURSE_API_KEY` is read first. If set and non-empty, it replaces `api_key` from config.
2. `DISCOURSE_API_USERNAME` is read first. If set and non-empty, it replaces `api_username` from config.
3. All other fields are config-only (no env override).

## Validation Errors

If validation fails, the tool exits with code 1 and prints to stderr:

```
error: config field '<field>' <reason>
```

Examples:
```
error: config field 'forum_url' is required
error: config field 'earliest_date' must be a date in YYYY-MM-DD format
error: config field 'max_retries' must be a positive integer
```
