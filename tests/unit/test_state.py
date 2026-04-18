import json
from pathlib import Path

import pytest

from discourse_retrieval.state import DownloadState


class TestDownloadStateSave:
    def test_save_writes_sidecar_json(self, tmp_path):
        md_path = tmp_path / "2024" / "03" / "my-topic.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text("# My Topic")

        state = DownloadState(thread_id=42, slug="my-topic", posts_count=7, downloaded_at="2026-04-18T10:00:00Z")
        state.save(md_path)

        sidecar = tmp_path / "2024" / "03" / "my-topic.state.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text())
        assert data["thread_id"] == 42
        assert data["slug"] == "my-topic"
        assert data["posts_count"] == 7
        assert data["downloaded_at"] == "2026-04-18T10:00:00Z"

    def test_save_overwrites_existing_sidecar(self, tmp_path):
        md_path = tmp_path / "my-topic.md"
        md_path.write_text("# Topic")

        DownloadState(thread_id=1, slug="t", posts_count=3, downloaded_at="2026-01-01T00:00:00Z").save(md_path)
        DownloadState(thread_id=1, slug="t", posts_count=5, downloaded_at="2026-04-18T00:00:00Z").save(md_path)

        data = json.loads((tmp_path / "my-topic.state.json").read_text())
        assert data["posts_count"] == 5


class TestDownloadStateLoad:
    def test_load_reads_sidecar(self, tmp_path):
        md_path = tmp_path / "my-topic.md"
        sidecar = tmp_path / "my-topic.state.json"
        sidecar.write_text(json.dumps({"thread_id": 99, "slug": "my-topic", "posts_count": 4, "downloaded_at": "2026-03-01T00:00:00Z"}))

        state = DownloadState.load(md_path)
        assert state is not None
        assert state.thread_id == 99
        assert state.posts_count == 4

    def test_load_returns_none_when_absent(self, tmp_path):
        md_path = tmp_path / "nonexistent.md"
        assert DownloadState.load(md_path) is None


class TestNeedsUpdate:
    def test_same_count_returns_false(self):
        state = DownloadState(thread_id=1, slug="t", posts_count=10, downloaded_at="2026-01-01T00:00:00Z")
        assert state.needs_update(10) is False

    def test_higher_count_returns_true(self):
        state = DownloadState(thread_id=1, slug="t", posts_count=10, downloaded_at="2026-01-01T00:00:00Z")
        assert state.needs_update(11) is True

    def test_lower_count_returns_false(self):
        # should not happen in practice, but guard against it
        state = DownloadState(thread_id=1, slug="t", posts_count=10, downloaded_at="2026-01-01T00:00:00Z")
        assert state.needs_update(9) is False


class TestNeedsDownload:
    def test_no_md_no_state_needs_download(self, tmp_path):
        md_path = tmp_path / "missing.md"
        assert DownloadState.needs_download(md_path) is True

    def test_md_exists_no_state_needs_download(self, tmp_path):
        md_path = tmp_path / "topic.md"
        md_path.write_text("# Topic")
        assert DownloadState.needs_download(md_path) is True

    def test_both_exist_does_not_need_download(self, tmp_path):
        md_path = tmp_path / "topic.md"
        md_path.write_text("# Topic")
        sidecar = tmp_path / "topic.state.json"
        sidecar.write_text(json.dumps({"thread_id": 1, "slug": "topic", "posts_count": 3, "downloaded_at": "2026-01-01T00:00:00Z"}))
        assert DownloadState.needs_download(md_path) is False
