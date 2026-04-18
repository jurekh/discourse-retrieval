from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from discourse_retrieval.client import DiscourseClient
from discourse_retrieval.config import Config

_EMPTY_TOPICS = {"topic_list": {"topics": []}}


def make_config(**kwargs) -> Config:
    defaults = {
        "forum_url": "https://forum.example.com",
        "api_key": "testkey",
        "output_dir": Path("/tmp/out"),
        "earliest_date": date(2024, 1, 1),
        "api_username": "testuser",
        "categories": [],
        "max_retries": 3,
    }
    defaults.update(kwargs)
    return Config(**defaults)


def make_response(
    status_code: int = 200,
    json_data: dict | None = None,
    headers: dict | None = None,
) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.headers = headers or {}
    r.raise_for_status = MagicMock()
    if status_code >= 400:
        r.raise_for_status.side_effect = requests.HTTPError(response=r)
    return r


class TestAuthHeaders:
    def test_api_key_header_on_every_request(self):
        cfg = make_config()
        client = DiscourseClient(cfg)
        resp = make_response(json_data=_EMPTY_TOPICS)
        with patch.object(client._session, "get", return_value=resp) as mock_get:
            client.list_topics(page=0)
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Api-Key"] == "testkey"

    def test_api_username_header_on_every_request(self):
        cfg = make_config(api_username="myuser")
        client = DiscourseClient(cfg)
        resp = make_response(json_data=_EMPTY_TOPICS)
        with patch.object(client._session, "get", return_value=resp) as mock_get:
            client.list_topics(page=0)
        _, kwargs = mock_get.call_args
        assert kwargs["headers"]["Api-Username"] == "myuser"


class TestListTopics:
    def test_list_topics_calls_correct_endpoint(self):
        cfg = make_config()
        client = DiscourseClient(cfg)
        t = {"id": 1, "slug": "t", "created_at": "2024-03-01T00:00:00.000Z", "posts_count": 5}
        resp = make_response(json_data={"topic_list": {"topics": [t]}})
        with patch.object(client._session, "get", return_value=resp) as mock_get:
            client.list_topics(page=2)
        assert mock_get.call_args[0][0] == "https://forum.example.com/latest.json"
        assert mock_get.call_args[1]["params"]["page"] == 2

    def test_list_topics_returns_topic_list(self):
        cfg = make_config()
        client = DiscourseClient(cfg)
        t = {"id": 1, "slug": "t", "created_at": "2024-03-01T00:00:00.000Z", "posts_count": 3}
        resp = make_response(json_data={"topic_list": {"topics": [t]}})
        with patch.object(client._session, "get", return_value=resp):
            result = client.list_topics(page=0)
        assert result == [t]


class TestListCategoryTopics:
    def test_calls_category_endpoint(self):
        cfg = make_config()
        client = DiscourseClient(cfg)
        with patch.object(
            client._session, "get", return_value=make_response(json_data=_EMPTY_TOPICS)
        ) as mock_get:
            client.list_category_topics(category_id=4, page=0)
        assert mock_get.call_args[0][0] == "https://forum.example.com/c/4/l/latest.json"


class TestGetTopic:
    def _topic_data(self) -> dict:
        return {"id": 42, "title": "Test", "posts_count": 3, "post_stream": {"posts": []}}

    def test_get_topic_calls_correct_endpoint(self):
        cfg = make_config()
        client = DiscourseClient(cfg)
        with patch.object(
            client._session, "get", return_value=make_response(json_data=self._topic_data())
        ) as mock_get:
            client.get_topic(topic_id=42)
        assert mock_get.call_args[0][0] == "https://forum.example.com/t/42.json"
        assert mock_get.call_args[1]["params"].get("include_raw") == 1

    def test_get_topic_returns_dict(self):
        cfg = make_config()
        client = DiscourseClient(cfg)
        data = self._topic_data()
        with patch.object(client._session, "get", return_value=make_response(json_data=data)):
            result = client.get_topic(topic_id=42)
        assert result == data


class TestGetTopicPostsCount:
    def test_returns_posts_count(self):
        cfg = make_config()
        client = DiscourseClient(cfg)
        resp = make_response(json_data={"posts_count": 17})
        with patch.object(client._session, "get", return_value=resp):
            count = client.get_topic_posts_count(topic_id=5)
        assert count == 17


class TestRetry:
    def test_retries_on_429(self):
        cfg = make_config(max_retries=3)
        client = DiscourseClient(cfg)
        responses = [
            make_response(429, headers={"Retry-After": "0"}),
            make_response(429, headers={"Retry-After": "0"}),
            make_response(200, json_data=_EMPTY_TOPICS),
        ]
        with patch.object(client._session, "get", side_effect=responses):
            with patch("time.sleep"):
                result = client.list_topics(page=0)
        assert result == []

    def test_raises_after_max_retries_exhausted(self):
        cfg = make_config(max_retries=2)
        client = DiscourseClient(cfg)
        responses = [make_response(429, headers={"Retry-After": "0"})] * 3
        with patch.object(client._session, "get", side_effect=responses):
            with patch("time.sleep"):
                with pytest.raises(RuntimeError, match="retries"):
                    client.list_topics(page=0)

    def test_exponential_backoff_used_without_retry_after(self):
        cfg = make_config(max_retries=3)
        client = DiscourseClient(cfg)
        responses = [
            make_response(429, headers={}),
            make_response(200, json_data=_EMPTY_TOPICS),
        ]
        sleep_calls: list[float] = []
        with patch.object(client._session, "get", side_effect=responses):
            with patch("time.sleep", side_effect=lambda s: sleep_calls.append(s)):
                client.list_topics(page=0)
        assert len(sleep_calls) == 1
        assert sleep_calls[0] >= 1
