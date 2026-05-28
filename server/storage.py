import hashlib
import re
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def tests_dir() -> Path:
    path = project_root() / "tests"
    path.mkdir(exist_ok=True)
    return path


def results_path() -> Path:
    return project_root() / "results.json"


def safe_test_filename(name: str) -> str:
    original = name.strip() or "test"
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", original)
    safe = re.sub(r"\s+", " ", safe).strip(" ._") or "test"
    if safe == original and len(safe) <= 100:
        return f"{safe}.json"
    digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:8]
    return f"{safe[:80]}_{digest}.json"


def test_path(name: str) -> Path:
    return tests_dir() / safe_test_filename(name)
