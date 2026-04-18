from pathlib import Path
from unittest.mock import patch

import pytest

from discourse_retrieval.cli import main


def _run(args: list[str]):
    with patch("sys.argv", ["discourse-retrieval", *args]):
        main()


class TestCliConfigLoading:
    def test_exits_1_when_config_file_not_found(self, tmp_path, capsys):
        missing = str(tmp_path / "nonexistent.toml")
        with pytest.raises(SystemExit) as exc:
            _run(["--config", missing])
        assert exc.value.code == 1
        assert "error:" in capsys.readouterr().err

    def test_exits_1_when_config_invalid(self, tmp_path, capsys):
        bad_cfg = tmp_path / "bad.toml"
        bad_cfg.write_text('forum_url = "not-a-url"\napi_key = "k"\n')
        with pytest.raises(SystemExit) as exc:
            _run(["--config", str(bad_cfg)])
        assert exc.value.code == 1
        assert "error:" in capsys.readouterr().err

    def test_uses_default_config_path(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc:
            _run([])
        assert exc.value.code == 1


class TestCliRun:
    def _valid_config(self, tmp_path: Path) -> Path:
        cfg = tmp_path / "config.toml"
        cfg.write_text(
            'forum_url = "https://forum.example.com"\n'
            'api_key = "k"\n'
            'api_username = "u"\n'
            'earliest_date = "2024-01-01"\n'
            f'output_dir = "{tmp_path}"\n'
        )
        return cfg

    def test_exits_2_on_runtime_error(self, tmp_path, capsys):
        cfg = self._valid_config(tmp_path)
        with patch("discourse_retrieval.cli.Archiver") as MockArchiver:
            MockArchiver.return_value.run.side_effect = RuntimeError("api down")
            with pytest.raises(SystemExit) as exc:
                _run(["--config", str(cfg)])
        assert exc.value.code == 2
        assert "error:" in capsys.readouterr().err

    def test_exits_3_on_os_error(self, tmp_path, capsys):
        cfg = self._valid_config(tmp_path)
        with patch("discourse_retrieval.cli.Archiver") as MockArchiver:
            MockArchiver.return_value.run.side_effect = OSError("disk full")
            with pytest.raises(SystemExit) as exc:
                _run(["--config", str(cfg)])
        assert exc.value.code == 3
        assert "error:" in capsys.readouterr().err

    def test_exits_0_on_success(self, tmp_path):
        cfg = self._valid_config(tmp_path)
        with patch("discourse_retrieval.cli.Archiver") as MockArchiver:
            MockArchiver.return_value.run.return_value = None
            _run(["--config", str(cfg)])
