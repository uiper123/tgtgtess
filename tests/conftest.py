"""Pytest fixtures shared across the test suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Делаем корень репозитория importable, чтобы `import shared.parser`
# работал без необходимости в `pip install -e .`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def tmp_test_file(tmp_path: Path):
    """
    Возвращает функцию-фабрику, которая записывает текст в tmp_path и
    отдаёт путь — удобно для проверок парсера.
    """

    def _make(content: str, filename: str = "test.txt") -> str:
        p = tmp_path / filename
        p.write_text(content, encoding="utf-8")
        return str(p)

    return _make
