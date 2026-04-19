import signal
from datetime import UTC, datetime
from pathlib import Path

from discourse_retrieval.client import DiscourseClient
from discourse_retrieval.config import Config
from discourse_retrieval.renderer import ThreadRenderer
from discourse_retrieval.state import ArchiveState, DownloadState


class Archiver:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = DiscourseClient(config)
        self._renderer = ThreadRenderer()
        self._interrupted = False

    def run(self) -> None:
        signal.signal(signal.SIGINT, self._handle_interrupt)
        output_dir = Path(self._config.output_dir)
        archive_state = ArchiveState.load(output_dir) or ArchiveState()
        archive_state.save(output_dir)

        downloaded = 0
        updated = 0
        skipped = 0

        try:
            for topic in self._iter_topics(archive_state):
                if self._interrupted:
                    break

                md_path = self._output_path(topic)
                should_dl, is_update = self._should_download(topic, md_path)

                prefix = f"[{md_path.parent.parent.name}/{md_path.parent.name}]"
                if not should_dl:
                    skipped += 1
                    print(f"{prefix} {md_path.name} (skip)")
                else:
                    self._download_thread(topic, md_path)
                    if is_update:
                        updated += 1
                        print(f"{prefix} {md_path.name} (update)")
                    else:
                        downloaded += 1
                        print(f"{prefix} {md_path.name}")

                if not archive_state.backfill_complete:
                    archive_state.update_cursor(topic["created_at"])
                    archive_state.save(output_dir)

        finally:
            signal.signal(signal.SIGINT, signal.SIG_DFL)

        if not self._interrupted:
            now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            archive_state.mark_complete(now)
            archive_state.save(output_dir)

        summary = f"Downloaded: {downloaded}, Updated: {updated}, Skipped: {skipped}"
        if self._interrupted:
            print(f"Interrupted. {summary} (resumable)")
        else:
            print(f"Done. {summary}")

    def _iter_topics(self, archive_state: ArchiveState):
        order = "activity" if archive_state.backfill_complete else "created"
        categories = self._config.categories
        if categories:
            for cat_id in categories:
                yield from self._paginate(
                    self._make_category_fetcher(cat_id, order), archive_state
                )
        else:
            yield from self._paginate(self._make_topic_fetcher(order), archive_state)

    def _paginate(self, fetch_page, archive_state: ArchiveState):
        cursor = archive_state.oldest_topic_date
        last_run = archive_state.last_run
        is_incremental = archive_state.backfill_complete
        page = 0
        while True:
            topics = fetch_page(page)
            if not topics:
                break
            stop_pagination = False
            all_old = True
            for topic in topics:
                created = _parse_dt(topic["created_at"]).date()
                if is_incremental:
                    bumped = topic.get("bumped_at") or topic["created_at"]
                    if bumped < last_run:
                        stop_pagination = True
                        break
                    if created >= self._config.earliest_date:
                        all_old = False
                        yield topic
                else:
                    if created >= self._config.earliest_date:
                        all_old = False
                        if cursor and topic["created_at"] > cursor:
                            continue  # fast-skip: already processed in prior run
                        yield topic
            if stop_pagination or all_old:
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

    def _make_topic_fetcher(self, order: str = "created"):
        def fetch(page: int) -> list[dict]:
            return self._client.list_topics(page, order=order)

        return fetch

    def _make_category_fetcher(self, cat_id: int, order: str = "created"):
        def fetch(page: int) -> list[dict]:
            return self._client.list_category_topics(cat_id, page, order=order)

        return fetch

    def _handle_interrupt(self, signum, frame) -> None:
        self._interrupted = True


def _parse_dt(dt_str: str) -> datetime:
    dt_str = dt_str.rstrip("Z").split(".")[0]
    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=UTC)
