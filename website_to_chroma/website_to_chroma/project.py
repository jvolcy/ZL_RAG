"""Project directory management, versioning, and staleness tracking."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sanitize_project_dirname(name: str) -> str:
    """Convert a project name into a safe subdirectory name."""
    cleaned = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("_")
    return cleaned or "project"


def _dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _dt_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


@dataclass
class RunRecord:
    path: str
    created_at: str
    input_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        return cls(
            path=data["path"],
            created_at=data["created_at"],
            input_path=data.get("input_path"),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "path": self.path,
            "created_at": self.created_at,
        }
        if self.input_path is not None:
            result["input_path"] = self.input_path
        return result


@dataclass
class StageHistory:
    latest: str | None = None
    runs: list[RunRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> StageHistory:
        if not data:
            return cls()
        runs = [RunRecord.from_dict(item) for item in data.get("runs", [])]
        return cls(latest=data.get("latest"), runs=runs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "latest": self.latest,
            "runs": [run.to_dict() for run in self.runs],
        }

    def add_run(self, path: Path, *, input_path: Path | None = None) -> RunRecord:
        record = RunRecord(
            path=str(path),
            created_at=_dt_to_iso(utc_now()),
            input_path=str(input_path) if input_path else None,
        )
        self.runs.append(record)
        self.latest = record.path
        return record


@dataclass
class ProjectManifest:
    name: str
    created_at: str
    crawl: StageHistory = field(default_factory=StageHistory)
    chunks: StageHistory = field(default_factory=StageHistory)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectManifest:
        return cls(
            name=data.get("name", "Untitled"),
            created_at=data.get("created_at", _dt_to_iso(utc_now())),
            crawl=StageHistory.from_dict(data.get("crawl")),
            chunks=StageHistory.from_dict(data.get("chunks")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "created_at": self.created_at,
            "crawl": self.crawl.to_dict(),
            "chunks": self.chunks.to_dict(),
        }


class Project:
    MANIFEST_NAME = "project.json"
    TAB1_CONFIG = "tab1_config.json"
    TAB2_CONFIG = "tab2_config.json"
    TAB3_CONFIG = "tab3_config.json"

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.manifest_path = self.root / self.MANIFEST_NAME
        self.manifest = self._load_manifest()

    @classmethod
    def create(cls, parent_dir: Path, name: str) -> Project:
        parent_dir = parent_dir.resolve()
        parent_dir.mkdir(parents=True, exist_ok=True)
        root = parent_dir / sanitize_project_dirname(name)
        if (root / cls.MANIFEST_NAME).exists():
            raise ValueError(f"A project already exists at {root}")
        root.mkdir(parents=True, exist_ok=True)
        (root / "outputs" / "crawl").mkdir(parents=True, exist_ok=True)
        (root / "outputs" / "chunks").mkdir(parents=True, exist_ok=True)
        (root / "chroma_db").mkdir(parents=True, exist_ok=True)
        project = cls(root)
        project.manifest = ProjectManifest(name=name, created_at=_dt_to_iso(utc_now()))
        project.save_manifest()
        return project

    @classmethod
    def open(cls, root: Path) -> Project:
        root = root.resolve()
        if not (root / cls.MANIFEST_NAME).exists():
            raise FileNotFoundError(f"No project found at {root}")
        return cls(root)

    def _load_manifest(self) -> ProjectManifest:
        if not self.manifest_path.exists():
            return ProjectManifest(name=self.root.name, created_at=_dt_to_iso(utc_now()))
        with self.manifest_path.open(encoding="utf-8") as fh:
            return ProjectManifest.from_dict(json.load(fh))

    def save_manifest(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("w", encoding="utf-8") as fh:
            json.dump(self.manifest.to_dict(), fh, indent=2)

    def config_path(self, tab: int) -> Path:
        names = {1: self.TAB1_CONFIG, 2: self.TAB2_CONFIG, 3: self.TAB3_CONFIG}
        return self.root / names[tab]

    def load_tab_config(self, tab: int, defaults: dict[str, Any]) -> dict[str, Any]:
        path = self.config_path(tab)
        if not path.exists():
            return dict(defaults)
        with path.open(encoding="utf-8") as fh:
            stored = json.load(fh)
        if not isinstance(stored, dict):
            return dict(defaults)
        merged = dict(defaults)
        merged.update(stored)
        return merged

    def save_tab_config(self, tab: int, config: dict[str, Any]) -> None:
        path = self.config_path(tab)
        self.root.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(config, fh, indent=2)

    def new_crawl_output_path(self) -> Path:
        stamp = utc_now().strftime("%Y%m%dT%H%M%S")
        return self.root / "outputs" / "crawl" / f"crawl_{stamp}.jsonl"

    def new_chunks_output_path(self) -> Path:
        stamp = utc_now().strftime("%Y%m%dT%H%M%S")
        return self.root / "outputs" / "chunks" / f"chunks_{stamp}.jsonl"

    def record_crawl_run(self, path: Path) -> RunRecord:
        record = self.manifest.crawl.add_run(path)
        self.save_manifest()
        return record

    def record_chunks_run(self, path: Path, *, input_path: Path) -> RunRecord:
        record = self.manifest.chunks.add_run(path, input_path=input_path)
        self.save_manifest()
        return record

    def latest_crawl_path(self) -> Path | None:
        if not self.manifest.crawl.latest:
            return None
        return Path(self.manifest.crawl.latest)

    def latest_chunks_path(self) -> Path | None:
        if not self.manifest.chunks.latest:
            return None
        return Path(self.manifest.chunks.latest)

    def staleness_warning(self, tab: int, selected_input: Path | None) -> str | None:
        if tab == 2:
            return self._input_staleness_warning(
                upstream_latest=self.latest_crawl_path(),
                selected_input=selected_input,
                upstream_label="crawl",
            )
        if tab == 3:
            return self._input_staleness_warning(
                upstream_latest=self.latest_chunks_path(),
                selected_input=selected_input,
                upstream_label="chunking",
            )
        return None

    @staticmethod
    def _input_staleness_warning(
        *,
        upstream_latest: Path | None,
        selected_input: Path | None,
        upstream_label: str,
    ) -> str | None:
        if upstream_latest is None or selected_input is None:
            return None
        if not upstream_latest.exists() or not selected_input.exists():
            return None
        if upstream_latest.resolve() == selected_input.resolve():
            return None
        return (
            f"A newer {upstream_label} output exists ({upstream_latest.name}). "
            f"The selected input ({selected_input.name}) may be stale."
        )
