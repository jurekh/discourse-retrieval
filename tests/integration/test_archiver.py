import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

from discourse_retrieval.archiver import Archiver
from discourse_retrieval.config import Config


def make_config(output_dir: Path) -> Config:
    return Config(
        forum_url="https://forum.example.com",
        api_key="testkey",
        output_dir=output_dir,
        earliest_date=date(2024, 1, 1),
        api_username="system",
        categories=[],
        max_retries=3,
    )


def make_topic(
    topic_id: int,
    slug: str,
    created_at: str,
    posts_count: int = 2,
    bumped_at: str | None = None,
) -> dict:
    t = {
        "id": topic_id,
        "title": f"Topic {topic_id}",
        "slug": slug,
        "created_at": created_at,
        "bumped_at": bumped_at or created_at,
        "posts_count": posts_count,
        "category_id": 4,
    }
    return t


def make_full_topic(topic_id: int, slug: str, created_at: str) -> dict:
    return {
        "id": topic_id,
        "title": f"Topic {topic_id}",
        "slug": slug,
        "created_at": created_at,
        "posts_count": 2,
        "category_id": 4,
        "details": {"category_name": "General"},
        "post_stream": {
            "posts": [
                {
                    "id": 1,
                    "post_number": 1,
                    "username": "alice",
                    "name": "Alice",
                    "created_at": created_at,
                    "raw": "First post body",
                    "cooked": "<p>First post body</p>",
                }
            ]
        },
    }


def make_config_with_categories(output_dir: Path, categories: list[int]) -> Config:
    return Config(
        forum_url="https://forum.example.com",
        api_key="testkey",
        output_dir=output_dir,
        earliest_date=date(2024, 1, 1),
        api_username="system",
        categories=categories,
        max_retries=3,
    )


class TestArchiverCategoryFilter:
    def test_uses_category_endpoint_when_categories_configured(self, tmp_path):
        cfg = make_config_with_categories(tmp_path, categories=[4, 7])
        topic = make_topic(1, "cat-topic", "2024-03-15T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_category_topics.side_effect = [[topic], [], [], []]
            mock_client.get_topic.return_value = make_full_topic(
                1, "cat-topic", "2024-03-15T10:00:00.000Z"
            )

            Archiver(cfg).run()

        mock_client.list_topics.assert_not_called()
        assert mock_client.list_category_topics.call_count >= 2
        calls = [c.args[0] for c in mock_client.list_category_topics.call_args_list]
        assert 4 in calls
        assert 7 in calls

    def test_uses_latest_endpoint_when_no_categories_configured(self, tmp_path):
        cfg = make_config(tmp_path)

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.return_value = []

            Archiver(cfg).run()

        mock_client.list_category_topics.assert_not_called()
        mock_client.list_topics.assert_called()


class TestArchiverDownload:
    def test_downloads_topics_within_date_range(self, tmp_path, capsys):
        cfg = make_config(tmp_path)
        topic_in = make_topic(1, "recent-topic", "2024-03-15T10:00:00.000Z")
        topic_out = make_topic(2, "old-topic", "2023-12-01T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            # page 0 returns both, page 1 returns empty (stops pagination)
            mock_client.list_topics.side_effect = [[topic_in, topic_out], []]
            mock_client.get_topic.return_value = make_full_topic(
                1, "recent-topic", "2024-03-15T10:00:00.000Z"
            )

            archiver = Archiver(cfg)
            archiver.run()

        # only recent-topic should be downloaded (old-topic predates earliest_date)
        md_file = tmp_path / "2024" / "03" / "recent-topic.md"
        assert md_file.exists(), f"Expected {md_file} to exist"
        old_file = tmp_path / "2023" / "12" / "old-topic.md"
        assert not old_file.exists()

    def test_writes_state_sidecar_alongside_md(self, tmp_path):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "my-topic", "2024-03-15T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[topic], []]
            mock_client.get_topic.return_value = make_full_topic(
                1, "my-topic", "2024-03-15T10:00:00.000Z"
            )

            Archiver(cfg).run()

        sidecar = tmp_path / "2024" / "03" / "my-topic.state.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text())
        assert data["thread_id"] == 1
        assert data["posts_count"] == 2

    def test_prints_progress_line_per_thread(self, tmp_path, capsys):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "progress-topic", "2024-03-15T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[topic], []]
            mock_client.get_topic.return_value = make_full_topic(
                1, "progress-topic", "2024-03-15T10:00:00.000Z"
            )

            Archiver(cfg).run()

        out = capsys.readouterr().out
        assert "[2024/03] progress-topic.md" in out

    def test_prints_summary_on_completion(self, tmp_path, capsys):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "sumtopic", "2024-03-15T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[topic], []]
            mock_client.get_topic.return_value = make_full_topic(
                1, "sumtopic", "2024-03-15T10:00:00.000Z"
            )

            Archiver(cfg).run()

        out = capsys.readouterr().out
        assert "Done." in out
        assert "Downloaded: 1" in out

    def test_stops_pagination_when_all_topics_old(self, tmp_path):
        cfg = make_config(tmp_path)
        old_topic = make_topic(2, "old-topic", "2023-06-01T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.return_value = [old_topic]

            Archiver(cfg).run()

        # pagination stops after first page (all topics old); get_topic never called
        mock_client.get_topic.assert_not_called()


class TestArchiverArchiveState:
    def test_clean_run_writes_archive_state_complete(self, tmp_path):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "my-topic", "2024-03-15T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[topic], []]
            mock_client.get_topic.return_value = make_full_topic(
                1, "my-topic", "2024-03-15T10:00:00.000Z"
            )
            Archiver(cfg).run()

        state_file = tmp_path / "archive.state.json"
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["backfill_complete"] is True
        assert data["last_run"] is not None

    def test_interrupted_run_does_not_set_backfill_complete(self, tmp_path):
        cfg = make_config(tmp_path)

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.return_value = []
            archiver = Archiver(cfg)
            archiver._interrupted = True
            archiver.run()

        state_file = tmp_path / "archive.state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text())
            assert data["backfill_complete"] is False

    def test_cursor_skips_topics_newer_than_oldest_topic_date(self, tmp_path):
        cfg = make_config(tmp_path)
        # Both topics have existing md+sidecar files (prior complete download).
        # Cursor sits between them. new_topic (above cursor) must be fast-skipped;
        # old_topic (below cursor) must be checked via get_topic_posts_count.
        new_topic = make_topic(1, "new-topic", "2024-06-01T00:00:00.000Z", posts_count=3)
        old_topic = make_topic(2, "old-topic", "2024-03-01T00:00:00.000Z", posts_count=3)

        for slug, dt in [("new-topic", "2024/06"), ("old-topic", "2024/03")]:
            md = tmp_path / dt / f"{slug}.md"
            md.parent.mkdir(parents=True, exist_ok=True)
            md.write_text("# content")
            sidecar_data = {
                "thread_id": 1 if slug == "new-topic" else 2,
                "slug": slug,
                "posts_count": 3,
                "downloaded_at": "2026-01-01T00:00:00Z",
            }
            (md.parent / f"{slug}.state.json").write_text(json.dumps(sidecar_data))

        from discourse_retrieval.state import ArchiveState

        ArchiveState(
            backfill_complete=False,
            last_run=None,
            oldest_topic_date="2024-04-01T00:00:00Z",
        ).save(tmp_path)

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[new_topic, old_topic], []]
            mock_client.get_topic_posts_count.return_value = 3  # unchanged
            Archiver(cfg).run()

        calls = [c.args[0] for c in mock_client.get_topic_posts_count.call_args_list]
        assert 1 not in calls  # new_topic (above cursor) must not be checked
        assert 2 in calls  # old_topic (below cursor) must be checked

    def test_incremental_mode_stops_at_last_run_boundary(self, tmp_path):
        cfg = make_config(tmp_path)
        recent_topic = make_topic(
            1, "recent", "2024-07-01T00:00:00.000Z", bumped_at="2024-07-01T00:00:00.000Z"
        )
        stale_topic = make_topic(
            2, "stale", "2024-04-01T00:00:00.000Z", bumped_at="2024-04-01T00:00:00.000Z"
        )

        from discourse_retrieval.state import ArchiveState

        ArchiveState(
            backfill_complete=True,
            last_run="2024-06-01T00:00:00Z",
            oldest_topic_date="2024-01-01T00:00:00Z",
        ).save(tmp_path)

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            # activity-sorted: recent topic first, then stale
            mock_client.list_topics.return_value = [recent_topic, stale_topic]
            mock_client.get_topic.return_value = make_full_topic(
                1, "recent", "2024-07-01T00:00:00.000Z"
            )
            Archiver(cfg).run()

        # stale_topic (bumped_at before last_run) must not be fetched
        fetched_ids = [c.args[0] for c in mock_client.get_topic.call_args_list]
        assert 2 not in fetched_ids
