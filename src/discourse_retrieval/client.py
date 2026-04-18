import time

import requests

from discourse_retrieval.config import Config


class DiscourseClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})

    def list_topics(self, page: int) -> list[dict]:
        url = f"{self._config.forum_url}/latest.json"
        data = self._get(url, params={"order": "created", "ascending": "false", "page": page})
        return data.get("topic_list", {}).get("topics", [])

    def list_category_topics(self, category_id: int, page: int) -> list[dict]:
        url = f"{self._config.forum_url}/c/{category_id}/l/latest.json"
        data = self._get(url, params={"page": page})
        return data.get("topic_list", {}).get("topics", [])

    def get_topic(self, topic_id: int) -> dict:
        url = f"{self._config.forum_url}/t/{topic_id}.json"
        return self._get(url, params={"include_raw": 1})

    def get_topic_posts_count(self, topic_id: int) -> int:
        url = f"{self._config.forum_url}/t/{topic_id}.json"
        data = self._get(url)
        return int(data["posts_count"])

    def _get(self, url: str, params: dict | None = None) -> dict:
        headers = {
            "Api-Key": self._config.api_key,
            "Api-Username": self._config.api_username,
        }
        attempt = 0
        while True:
            response = self._session.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 429:
                attempt += 1
                if attempt >= self._config.max_retries:
                    raise RuntimeError(
                        f"API request failed after {self._config.max_retries} retries: "
                        "429 Too Many Requests"
                    )
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    time.sleep(float(retry_after))
                else:
                    time.sleep(2**attempt)
                continue
            response.raise_for_status()
            return response.json()
