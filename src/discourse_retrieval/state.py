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
