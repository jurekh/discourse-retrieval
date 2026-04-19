import json

from discourse_retrieval.state import ArchiveState, DownloadState

_DT = "2026-04-18T10:00:00Z"
_DT2 = "2026-01-01T00:00:00Z"


def _state(posts_count: int = 7) -> DownloadState:
    return DownloadState(thread_id=42, slug="my-topic", posts_count=posts_count, downloaded_at=_DT)


class TestDownloadStateSave:
    def test_save_writes_sidecar_json(self, tmp_path):
        md_path = tmp_path / "2024" / "03" / "my-topic.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text("# My Topic")

        _state(7).save(md_path)

        sidecar = tmp_path / "2024" / "03" / "my-topic.state.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text())
        assert data["thread_id"] == 42
        assert data["slug"] == "my-topic"
        assert data["posts_count"] == 7
        assert data["downloaded_at"] == _DT

    def test_save_overwrites_existing_sidecar(self, tmp_path):
        md_path = tmp_path / "my-topic.md"
        md_path.write_text("# Topic")

        DownloadState(thread_id=1, slug="t", posts_count=3, downloaded_at=_DT2).save(md_path)
        DownloadState(thread_id=1, slug="t", posts_count=5, downloaded_at=_DT).save(md_path)

        data = json.loads((tmp_path / "my-topic.state.json").read_text())
        assert data["posts_count"] == 5


class TestDownloadStateLoad:
    def test_load_reads_sidecar(self, tmp_path):
        md_path = tmp_path / "my-topic.md"
        sidecar = tmp_path / "my-topic.state.json"
        data = {"thread_id": 99, "slug": "my-topic", "posts_count": 4, "downloaded_at": _DT2}
        sidecar.write_text(json.dumps(data))

        state = DownloadState.load(md_path)
        assert state is not None
        assert state.thread_id == 99
        assert state.posts_count == 4

    def test_load_returns_none_when_absent(self, tmp_path):
        assert DownloadState.load(tmp_path / "nonexistent.md") is None


class TestNeedsUpdate:
    def test_same_count_returns_false(self):
        assert _state(10).needs_update(10) is False

    def test_higher_count_returns_true(self):
        assert _state(10).needs_update(11) is True

    def test_lower_count_returns_false(self):
        # guard: posts_count shouldn't decrease, but ignore if it does
        assert _state(10).needs_update(9) is False


class TestArchiveStateSave:
    def test_save_writes_archive_state_json(self, tmp_path):
        ArchiveState(backfill_complete=False, last_run=None, oldest_topic_date=None).save(tmp_path)
        assert (tmp_path / "archive.state.json").exists()

    def test_save_overwrites_existing(self, tmp_path):
        ArchiveState(
            backfill_complete=False, last_run=None, oldest_topic_date="2024-01-01T00:00:00Z"
        ).save(tmp_path)
        ArchiveState(
            backfill_complete=True, last_run=_DT, oldest_topic_date="2024-01-01T00:00:00Z"
        ).save(tmp_path)
        data = json.loads((tmp_path / "archive.state.json").read_text())
        assert data["backfill_complete"] is True
        assert data["last_run"] == _DT


class TestArchiveStateLoad:
    def test_load_reads_file(self, tmp_path):
        (tmp_path / "archive.state.json").write_text(
            json.dumps({"backfill_complete": True, "last_run": _DT, "oldest_topic_date": _DT2})
        )
        state = ArchiveState.load(tmp_path)
        assert state is not None
        assert state.backfill_complete is True
        assert state.last_run == _DT
        assert state.oldest_topic_date == _DT2

    def test_load_returns_none_when_absent(self, tmp_path):
        assert ArchiveState.load(tmp_path) is None


class TestArchiveStateUpdateCursor:
    def test_update_cursor_sets_date_when_none(self):
        s = ArchiveState()
        s.update_cursor("2024-03-01T00:00:00Z")
        assert s.oldest_topic_date == "2024-03-01T00:00:00Z"

    def test_update_cursor_keeps_minimum(self):
        s = ArchiveState(oldest_topic_date="2024-03-01T00:00:00Z")
        s.update_cursor("2024-06-01T00:00:00Z")  # newer - should not replace
        assert s.oldest_topic_date == "2024-03-01T00:00:00Z"
        s.update_cursor("2024-01-01T00:00:00Z")  # older - should replace
        assert s.oldest_topic_date == "2024-01-01T00:00:00Z"

    def test_update_cursor_does_not_change_backfill_or_last_run(self):
        s = ArchiveState(backfill_complete=False, last_run=_DT)
        s.update_cursor("2024-03-01T00:00:00Z")
        assert s.backfill_complete is False
        assert s.last_run == _DT


class TestArchiveStateMarkComplete:
    def test_mark_complete_sets_fields(self):
        s = ArchiveState()
        s.mark_complete(_DT)
        assert s.backfill_complete is True
        assert s.last_run == _DT

    def test_mark_complete_does_not_clear_cursor(self):
        s = ArchiveState(oldest_topic_date=_DT2)
        s.mark_complete(_DT)
        assert s.oldest_topic_date == _DT2


class TestNeedsDownload:
    def test_no_md_no_state_needs_download(self, tmp_path):
        assert DownloadState.needs_download(tmp_path / "missing.md") is True

    def test_md_exists_no_state_needs_download(self, tmp_path):
        md_path = tmp_path / "topic.md"
        md_path.write_text("# Topic")
        assert DownloadState.needs_download(md_path) is True

    def test_both_exist_does_not_need_download(self, tmp_path):
        md_path = tmp_path / "topic.md"
        md_path.write_text("# Topic")
        (tmp_path / "topic.state.json").write_text(
            json.dumps({"thread_id": 1, "slug": "topic", "posts_count": 3, "downloaded_at": _DT2})
        )
        assert DownloadState.needs_download(md_path) is False
