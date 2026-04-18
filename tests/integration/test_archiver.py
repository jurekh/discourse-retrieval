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


def make_topic(topic_id: int, slug: str, created_at: str, posts_count: int = 2) -> dict:
    return {
        "id": topic_id,
        "title": f"Topic {topic_id}",
        "slug": slug,
        "created_at": created_at,
        "posts_count": posts_count,
        "category_id": 4,
    }


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
