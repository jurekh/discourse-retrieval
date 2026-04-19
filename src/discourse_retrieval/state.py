import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class DownloadState:
    thread_id: int
    slug: str
    posts_count: int
    downloaded_at: str  # ISO 8601 UTC string

    def save(self, md_path: Path) -> None:
        sidecar = _sidecar_path(md_path)
        sidecar.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls, md_path: Path) -> "DownloadState | None":
        sidecar = _sidecar_path(md_path)
        if not sidecar.exists():
            return None
        data = json.loads(sidecar.read_text())
        return cls(**data)

    def needs_update(self, current_posts_count: int) -> bool:
        return current_posts_count > self.posts_count

    @staticmethod
    def needs_download(md_path: Path) -> bool:
        if not md_path.exists():
            return True
        return not _sidecar_path(md_path).exists()


def _sidecar_path(md_path: Path) -> Path:
    return md_path.with_suffix(".state.json")


_ARCHIVE_STATE_FILE = "archive.state.json"


@dataclass
class ArchiveState:
    backfill_complete: bool = False
    last_run: str | None = None
    oldest_topic_date: str | None = None

    def save(self, output_dir: Path) -> None:
        path = output_dir / _ARCHIVE_STATE_FILE
        tmp = path.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(asdict(self), indent=2))
            tmp.rename(path)
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, output_dir: Path) -> "ArchiveState | None":
        path = output_dir / _ARCHIVE_STATE_FILE
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return cls(**data)

    def update_cursor(self, topic_date: str) -> None:
        if self.oldest_topic_date is None or topic_date < self.oldest_topic_date:
            self.oldest_topic_date = topic_date

    def mark_complete(self, now: str) -> None:
        self.backfill_complete = True
        self.last_run = now
