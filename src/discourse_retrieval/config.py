import os
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Config:
    forum_url: str
    api_key: str
    output_dir: Path
    earliest_date: date
    api_username: str = "system"
    categories: list[int] = field(default_factory=list)
    max_retries: int = 5

    @classmethod
    def from_file(cls, path: Path) -> "Config":
        with open(path, "rb") as f:
            data = dict(tomllib.load(f))

        env_key = os.environ.get("DISCOURSE_API_KEY", "")
        if env_key:
            data["api_key"] = env_key

        env_user = os.environ.get("DISCOURSE_API_USERNAME", "")
        if env_user:
            data["api_username"] = env_user

        _require(data, "forum_url")
        _require(data, "api_key")
        _require(data, "output_dir")
        _require(data, "earliest_date")

        forum_url = data["forum_url"]
        if not (forum_url.startswith("http://") or forum_url.startswith("https://")):
            raise ValueError("config field 'forum_url' must start with http:// or https://")

        try:
            earliest_date = date.fromisoformat(data["earliest_date"])
        except (ValueError, TypeError):
            raise ValueError("config field 'earliest_date' must be a date in YYYY-MM-DD format")

        max_retries = data.get("max_retries", 5)
        if not isinstance(max_retries, int) or max_retries < 1:
            raise ValueError("config field 'max_retries' must be a positive integer")

        return cls(
            forum_url=forum_url,
            api_key=data["api_key"],
            output_dir=Path(data["output_dir"]),
            earliest_date=earliest_date,
            api_username=data.get("api_username", "system"),
            categories=list(data.get("categories", [])),
            max_retries=max_retries,
        )


def _require(data: dict, field_name: str) -> None:
    if field_name not in data or not data[field_name]:
        raise ValueError(f"config field '{field_name}' is required")
