import json
import signal
from datetime import date
from pathlib import Path
from unittest.mock import patch

from discourse_retrieval.archiver import Archiver
from discourse_retrieval.config import Config

_PRIOR_STATE = {
    "thread_id": 1,
    "slug": "my-topic",
    "posts_count": 2,
    "downloaded_at": "2026-01-01T00:00:00Z",
}


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


def make_topic(topic_id: int, slug: str, created_at: str) -> dict:
    return {
        "id": topic_id,
        "title": f"Topic {topic_id}",
        "slug": slug,
        "created_at": created_at,
        "posts_count": 2,
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
                    "raw": "Body",
                    "cooked": "<p>Body</p>",
                }
            ]
        },
    }


class TestArchiverSignalHandling:
    def test_sigint_handler_registered_on_run(self, tmp_path):
        cfg = make_config(tmp_path)
        registered = {}

        def fake_signal(sig, handler):
            registered[sig] = handler

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.return_value = []
            with patch("signal.signal", side_effect=fake_signal):
                Archiver(cfg).run()

        assert signal.SIGINT in registered

    def test_interrupted_flag_causes_clean_exit(self, tmp_path, capsys):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "topic-a", "2024-03-15T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.return_value = [topic]
            mock_client.get_topic.return_value = make_full_topic(
                1, "topic-a", "2024-03-15T10:00:00.000Z"
            )

            archiver = Archiver(cfg)
            archiver._interrupted = True
            archiver.run()

        out = capsys.readouterr().out
        assert "Interrupted." in out
        assert "(resumable)" in out

    def test_interrupted_summary_shows_counts(self, tmp_path, capsys):
        cfg = make_config(tmp_path)

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.return_value = []
            archiver = Archiver(cfg)
            archiver._interrupted = True
            archiver.run()

        out = capsys.readouterr().out
        assert "Downloaded: 0" in out
        assert "Skipped: 0" in out


class TestArchiverAtomicWrite:
    def test_no_partial_md_on_write_failure(self, tmp_path):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "fail-topic", "2024-03-15T10:00:00.000Z")
        full = make_full_topic(1, "fail-topic", "2024-03-15T10:00:00.000Z")

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[topic], []]
            mock_client.get_topic.return_value = full

            with patch("pathlib.Path.rename", side_effect=OSError("disk full")):
                try:
                    Archiver(cfg).run()
                except OSError:
                    pass

        md_path = tmp_path / "2024" / "03" / "fail-topic.md"
        assert not md_path.exists()
        assert not md_path.with_suffix(".md.tmp").exists()


class TestArchiverResume:
    def test_skips_up_to_date_thread(self, tmp_path, capsys):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "my-topic", "2024-03-15T10:00:00.000Z")

        # pre-create md and state files to simulate a prior complete download
        md_path = tmp_path / "2024" / "03" / "my-topic.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text("# Already downloaded")
        state_path = tmp_path / "2024" / "03" / "my-topic.state.json"
        state_path.write_text(json.dumps(_PRIOR_STATE))

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[topic], []]
            # posts count unchanged -> should skip
            mock_client.get_topic_posts_count.return_value = 2

            Archiver(cfg).run()

        out = capsys.readouterr().out
        assert "Skipped: 1" in out
        mock_client.get_topic.assert_not_called()

    def test_redownloads_thread_with_new_replies(self, tmp_path, capsys):
        cfg = make_config(tmp_path)
        topic = make_topic(1, "my-topic", "2024-03-15T10:00:00.000Z")

        md_path = tmp_path / "2024" / "03" / "my-topic.md"
        md_path.parent.mkdir(parents=True)
        md_path.write_text("# Old content")
        state_path = tmp_path / "2024" / "03" / "my-topic.state.json"
        state_path.write_text(json.dumps(_PRIOR_STATE))

        with patch("discourse_retrieval.archiver.DiscourseClient") as MockClient:
            mock_client = MockClient.return_value
            mock_client.list_topics.side_effect = [[topic], []]
            # forum now has 5 posts -> needs update
            mock_client.get_topic_posts_count.return_value = 5
            mock_client.get_topic.return_value = make_full_topic(
                1, "my-topic", "2024-03-15T10:00:00.000Z"
            )

            Archiver(cfg).run()

        out = capsys.readouterr().out
        assert "Updated: 1" in out
        mock_client.get_topic.assert_called_once()
