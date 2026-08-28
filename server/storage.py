import hashlib
import os
import re
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_tests_dir() -> Path:
    """Возвращает стандартную папку для хранения тестов."""
    path = project_root() / "tests_repo"
    path.mkdir(parents=True, exist_ok=True)
    return path


def tests_dir() -> Path:
    """
    Возвращает текущую активную директорию репозитория тестов.
    Если пользователь указал свою директорию в настройках, используется она.
    Иначе используется стандартная папка tests_repo/.
    """
    try:
        from PySide6.QtCore import QSettings
        settings = QSettings("EduTest", "Server")
        custom_dir = settings.value("tests_directory", "", type=str).strip()
        if custom_dir:
            path = Path(custom_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path
    except Exception:
        pass

    repo_path = project_root() / "tests_repo"
    if not repo_path.exists():
        repo_path.mkdir(parents=True, exist_ok=True)
        old_path = project_root() / "tests"
        if old_path.exists():
            for f in old_path.glob("*.json"):
                target = repo_path / f.name
                if not target.exists():
                    try:
                        target.write_bytes(f.read_bytes())
                    except Exception:
                        pass
    else:
        repo_path.mkdir(parents=True, exist_ok=True)

    return repo_path


def set_custom_tests_dir(directory: str | Path | None) -> Path:
    """Устанавливает или сбрасывает пользовательскую директорию для тестов."""
    from PySide6.QtCore import QSettings
    settings = QSettings("EduTest", "Server")
    if directory:
        p = Path(directory)
        p.mkdir(parents=True, exist_ok=True)
        settings.setValue("tests_directory", str(p.resolve()))
        settings.sync()
        return p
    else:
        settings.remove("tests_directory")
        settings.sync()
        return default_tests_dir()


def results_path() -> Path:
    return project_root() / "results.json"


def safe_test_filename(name: str, ext: str = ".txt") -> str:
    original = name.strip() or "test"
    # Убираем расширение, если оно уже передано
    base_name = original
    for known_ext in (".txt", ".json", ".log"):
        if base_name.lower().endswith(known_ext):
            base_name = base_name[:-len(known_ext)]
            break

    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", base_name)
    safe = re.sub(r"\s+", " ", safe).strip(" ._") or "test"
    if safe == base_name and len(safe) <= 100:
        return f"{safe}{ext}"
    digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:8]
    return f"{safe[:80]}_{digest}{ext}"


def test_path(name: str) -> Path:
    """Возвращает путь к файлу теста в директории тестов (.txt или .json)."""
    d = tests_dir()
    txt_file = d / safe_test_filename(name, ext=".txt")
    if txt_file.exists():
        return txt_file
    json_file = d / safe_test_filename(name, ext=".json")
    if json_file.exists():
        return json_file
    return txt_file
