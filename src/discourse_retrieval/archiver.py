import signal
from datetime import UTC, datetime
from pathlib import Path

from discourse_retrieval.client import DiscourseClient
from discourse_retrieval.config import Config
from discourse_retrieval.renderer import ThreadRenderer
from discourse_retrieval.state import DownloadState


class Archiver:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = DiscourseClient(config)
        self._renderer = ThreadRenderer()
        self._interrupted = False

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._handle_interrupt)

        downloaded = 0
        updated = 0
        skipped = 0

        try:
            for topic in self._iter_topics():
                if self._interrupted:
                    break

                md_path = self._output_path(topic)
                should_dl, is_update = self._should_download(topic, md_path)

                if not should_dl:
                    skipped += 1
                    continue

                self._download_thread(topic, md_path)
                if is_update:
                    updated += 1
                else:
                    downloaded += 1
                print(f"[{md_path.parent.parent.name}/{md_path.parent.name}] {md_path.name}")

        finally:
            signal.signal(signal.SIGINT, signal.SIG_DFL)

        summary = f"Downloaded: {downloaded}, Updated: {updated}, Skipped: {skipped}"
        if self._interrupted:
            print(f"Interrupted. {summary} (resumable)")
        else:
            print(f"Done. {summary}")

    def _iter_topics(self):
        categories = self._config.categories
        if categories:
            for cat_id in categories:
                yield from self._paginate(self._make_category_fetcher(cat_id))
        else:
            yield from self._paginate(self._client.list_topics)

    def _paginate(self, fetch_page):
        page = 0
        while True:
            topics = fetch_page(page)
            if not topics:
                break
            all_old = True
            for topic in topics:
                created = _parse_dt(topic["created_at"]).date()
                if created >= self._config.earliest_date:
                    all_old = False
                    yield topic
            if all_old:
                break
            page += 1

    def _output_path(self, topic: dict) -> Path:
        created = _parse_dt(topic["created_at"])
        return (
            Path(self._config.output_dir)
            / f"{created.year:04d}"
            / f"{created.month:02d}"
            / f"{topic['slug']}.md"
        )

    def _should_download(self, topic: dict, md_path: Path) -> tuple[bool, bool]:
        if DownloadState.needs_download(md_path):
            return True, False
        state = DownloadState.load(md_path)
        if state is None:
            return True, False
        current_count = self._client.get_topic_posts_count(topic["id"])
        if state.needs_update(current_count):
            return True, True
        return False, False

    def _download_thread(self, topic: dict, md_path: Path) -> None:
        full_topic = self._client.get_topic(topic["id"])
        content = self._renderer.render(full_topic)

        md_path.parent.mkdir(parents=True, exist_ok=True)

        # atomic write: write to temp file then rename
        tmp = md_path.with_suffix(".md.tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            tmp.rename(md_path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        state = DownloadState(
            thread_id=full_topic["id"],
            slug=full_topic["slug"],
            posts_count=full_topic["posts_count"],
            downloaded_at=now,
        )
        state.save(md_path)

    def _make_category_fetcher(self, cat_id: int):
        def fetch(page: int) -> list[dict]:
            return self._client.list_category_topics(cat_id, page)

        return fetch

    def _handle_interrupt(self, signum, frame) -> None:
        self._interrupted = True


def _parse_dt(dt_str: str) -> datetime:
    dt_str = dt_str.rstrip("Z").split(".")[0]
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
