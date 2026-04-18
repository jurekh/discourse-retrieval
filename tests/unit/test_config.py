import os
import textwrap
from datetime import date
from pathlib import Path

import pytest

from discourse_retrieval.config import Config


def write_toml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(textwrap.dedent(content))
    return p


class TestConfigLoading:
    def test_minimal_valid_config(self, tmp_path):
        p = write_toml(
            tmp_path,
            """
            forum_url = "https://forum.example.com"
            api_key = "secret"
            output_dir = "/tmp/out"
            earliest_date = "2024-01-01"
            """,
        )
        cfg = Config.from_file(p)
        assert cfg.forum_url == "https://forum.example.com"
        assert cfg.api_key == "secret"
        assert cfg.output_dir == Path("/tmp/out")
        assert cfg.earliest_date == date(2024, 1, 1)
        assert cfg.categories == []
        assert cfg.max_retries == 5
        assert cfg.api_username == "system"

    def test_full_config(self, tmp_path):
        p = write_toml(
            tmp_path,
            """
            forum_url = "https://forum.example.com"
            api_key = "secret"
            api_username = "myuser"
            output_dir = "/tmp/out"
            earliest_date = "2024-06-15"
            categories = [4, 7, 12]
            max_retries = 3
            """,
        )
        cfg = Config.from_file(p)
        assert cfg.api_username == "myuser"
        assert cfg.categories == [4, 7, 12]
        assert cfg.max_retries == 3
        assert cfg.earliest_date == date(2024, 6, 15)

    def test_env_overrides_api_key(self, tmp_path, monkeypatch):
        p = write_toml(
            tmp_path,
            """
            forum_url = "https://forum.example.com"
            api_key = "from-file"
            output_dir = "/tmp/out"
            earliest_date = "2024-01-01"
            """,
        )
        monkeypatch.setenv("DISCOURSE_API_KEY", "from-env")
        cfg = Config.from_file(p)
        assert cfg.api_key == "from-env"

    def test_env_overrides_api_username(self, tmp_path, monkeypatch):
        p = write_toml(
            tmp_path,
            """
            forum_url = "https://forum.example.com"
            api_key = "secret"
            api_username = "from-file"
            output_dir = "/tmp/out"
            earliest_date = "2024-01-01"
            """,
        )
        monkeypatch.setenv("DISCOURSE_API_USERNAME", "from-env")
        cfg = Config.from_file(p)
        assert cfg.api_username == "from-env"

    def test_empty_env_does_not_override(self, tmp_path, monkeypatch):
        p = write_toml(
            tmp_path,
            """
            forum_url = "https://forum.example.com"
            api_key = "from-file"
            output_dir = "/tmp/out"
            earliest_date = "2024-01-01"
            """,
        )
        monkeypatch.setenv("DISCOURSE_API_KEY", "")
        cfg = Config.from_file(p)
        assert cfg.api_key == "from-file"


class TestConfigValidation:
    def _base(self, **overrides) -> dict:
        base = {
            "forum_url": '"https://forum.example.com"',
            "api_key": '"secret"',
            "output_dir": '"/tmp/out"',
            "earliest_date": '"2024-01-01"',
        }
        base.update(overrides)
        return base

    def _write(self, tmp_path: Path, fields: dict) -> Path:
        lines = "\n".join(f"{k} = {v}" for k, v in fields.items())
        return write_toml(tmp_path, lines)

    def test_missing_forum_url_raises(self, tmp_path):
        fields = self._base()
        del fields["forum_url"]
        with pytest.raises(ValueError, match="forum_url"):
            Config.from_file(self._write(tmp_path, fields))

    def test_missing_api_key_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("DISCOURSE_API_KEY", raising=False)
        fields = self._base()
        del fields["api_key"]
        with pytest.raises(ValueError, match="api_key"):
            Config.from_file(self._write(tmp_path, fields))

    def test_missing_output_dir_raises(self, tmp_path):
        fields = self._base()
        del fields["output_dir"]
        with pytest.raises(ValueError, match="output_dir"):
            Config.from_file(self._write(tmp_path, fields))

    def test_missing_earliest_date_raises(self, tmp_path):
        fields = self._base()
        del fields["earliest_date"]
        with pytest.raises(ValueError, match="earliest_date"):
            Config.from_file(self._write(tmp_path, fields))

    def test_invalid_forum_url_no_scheme(self, tmp_path):
        fields = self._base(forum_url='"forum.example.com"')
        with pytest.raises(ValueError, match="forum_url"):
            Config.from_file(self._write(tmp_path, fields))

    def test_invalid_earliest_date_format(self, tmp_path):
        fields = self._base(earliest_date='"01-01-2024"')
        with pytest.raises(ValueError, match="earliest_date"):
            Config.from_file(self._write(tmp_path, fields))

    def test_invalid_max_retries_zero(self, tmp_path):
        fields = self._base(max_retries="0")
        with pytest.raises(ValueError, match="max_retries"):
            Config.from_file(self._write(tmp_path, fields))

    def test_invalid_max_retries_negative(self, tmp_path):
        fields = self._base(max_retries="-1")
        with pytest.raises(ValueError, match="max_retries"):
            Config.from_file(self._write(tmp_path, fields))

    def test_categories_defaults_to_empty_list(self, tmp_path):
        fields = self._base()
        cfg = Config.from_file(self._write(tmp_path, fields))
        assert cfg.categories == []
