import hashlib
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
    """
    Возвращает путь к файлу теста в директории тестов (.txt или .json).
    Поддерживает вложенные группы тестов (например 'Информатика / М-25'),
    прямые имена файлов и рекурсивный поиск.
    """
    d = tests_dir()
    if not name:
        return d / "test.txt"

    # 0. Если передан уже существующий абсолютный или относительный путь
    p = Path(name)
    if p.exists() and p.is_file():
        return p

    # 1. Прямой поиск в корне активной директории
    for ext in (".txt", ".json", ""):
        target = d / f"{name}{ext}"
        if target.exists() and target.is_file():
            return target
        safe_target = d / safe_test_filename(name, ext=ext if ext else ".txt")
        if safe_target.exists() and safe_target.is_file():
            return safe_target

    # 2. Если группа содержит разделитель подпапок ' / ' или '/' или '\'
    parts = [part.strip() for part in re.split(r'\s*/\s*|\s*\\\\\s*', name) if part.strip()]
    if len(parts) > 1:
        for ext in (".txt", ".json", ""):
            sub = d.joinpath(*parts[:-1]) / f"{parts[-1]}{ext}"
            if sub.exists() and sub.is_file():
                return sub
            sub_safe = d.joinpath(*parts[:-1]) / safe_test_filename(parts[-1], ext=ext if ext else ".txt")
            if sub_safe.exists() and sub_safe.is_file():
                return sub_safe

    # 3. Рекурсивный поиск fallback по имени/стэму файла
    stem = parts[-1] if parts else name
    for ext in ("*.txt", "*.json"):
        for match in d.rglob(ext):
            if match.stem == stem or match.stem.strip() == stem or match.name == name:
                return match

    # 4. Если файл новый и еще не существует
    if len(parts) > 1:
        target_new = d.joinpath(*parts[:-1]) / safe_test_filename(parts[-1], ext=".txt")
        target_new.parent.mkdir(parents=True, exist_ok=True)
        return target_new

    return d / safe_test_filename(name, ext=".txt")
