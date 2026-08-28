"""
Тесты управления директорией хранения и загрузки тестов в формате .txt.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import server.storage as storage
from shared.parser import parse_test_file, save_test_to_txt, serialize_test_to_txt


def test_default_tests_directory():
    d = storage.default_tests_dir()
    assert d.exists()
    assert d.is_dir()
    assert "tests_repo" in str(d)


def test_custom_tests_directory(tmp_path: Path):
    custom = tmp_path / "my_custom_exam_bank"
    storage.set_custom_tests_dir(custom)

    active = storage.tests_dir()
    assert active.resolve() == custom.resolve()
    assert active.exists()

    # Проверяем формирование пути к тесту (по умолчанию .txt)
    tp = storage.test_path("Контрольная работа №1")
    assert str(tp).startswith(str(custom.resolve()))
    assert tp.name.endswith(".txt")

    # Сбрасываем назад к дефолту
    storage.set_custom_tests_dir(None)
    assert storage.tests_dir().resolve() == storage.default_tests_dir().resolve()


def test_serialize_and_parse_txt_roundtrip(tmp_path: Path):
    questions = [
        {
            "number": 1,
            "text": "Сколько бит в одном байте?",
            "multiple": False,
            "written": False,
            "matching": False,
            "ordering": False,
            "blanks": False,
            "answers": [
                {"text": "8", "correct": True},
                {"text": "16", "correct": False},
                {"text": "4", "correct": False},
            ],
        },
        {
            "number": 2,
            "text": "Выберите протоколы прикладного уровня",
            "multiple": True,
            "written": False,
            "matching": False,
            "ordering": False,
            "blanks": False,
            "answers": [
                {"text": "HTTP", "correct": True},
                {"text": "DNS", "correct": True},
                {"text": "IP", "correct": False},
            ],
        },
        {
            "number": 3,
            "text": "Сопоставьте порт и протокол",
            "multiple": False,
            "written": False,
            "matching": True,
            "ordering": False,
            "blanks": False,
            "answers": [
                {"text": "80 = HTTP", "key": "80", "value": "HTTP", "correct": True},
                {"text": "443 = HTTPS", "key": "443", "value": "HTTPS", "correct": True},
            ],
        },
    ]

    test_file = tmp_path / "exam_networks.txt"
    save_test_to_txt(
        test_file,
        title="Экзамен по компьютерным сетям",
        section="Сетевые протоколы",
        questions=questions,
    )

    assert test_file.exists()
    content = test_file.read_text(encoding="utf-8")
    assert "@title: Экзамен по компьютерным сетям" in content
    assert "@section: Сетевые протоколы" in content
    assert "? Сколько бит в одном байте?" in content
    assert "? (С множественным выбором) Выберите протоколы прикладного уровня" in content
    assert "? (Соответствие) Сопоставьте порт и протокол" in content

    # Читаем обратно через parse_test_file
    parsed = parse_test_file(str(test_file))
    assert getattr(parsed, "title", None) == "Экзамен по компьютерным сетям"
    assert getattr(parsed, "section", None) == "Сетевые протоколы"
    assert len(parsed) == 3
    assert parsed[0]["text"] == "Сколько бит в одном байте?"
    assert parsed[1]["multiple"] is True
    assert parsed[2]["matching"] is True


def test_empty_test_file_allow_empty(tmp_path: Path):
    empty_test = tmp_path / "new_empty_test.txt"
    save_test_to_txt(empty_test, title="Новый пустой тест", section="Раздел 1", questions=[])
    assert empty_test.exists()

    parsed = parse_test_file(str(empty_test), allow_empty=True)
    assert len(parsed) == 0
    assert getattr(parsed, "title", None) == "Новый пустой тест"
    assert getattr(parsed, "section", None) == "Раздел 1"


def test_nested_tests_in_subfolders(tmp_path: Path):
    storage.set_custom_tests_dir(tmp_path)

    sub1 = tmp_path / "Информатика"
    sub1.mkdir()
    f1 = sub1 / "М-25.txt"
    f1.write_text("@title: Информатика М-25\n? Вопрос\n+ Ответ\n", encoding="utf-8")

    sub2 = tmp_path / "ИСП-23"
    sub2.mkdir()
    f2 = sub2 / "МДК 05.02.txt"
    f2.write_text("@title: МДК 05.02\n? Вопрос\n+ Ответ\n", encoding="utf-8")

    # 1. Проверяем поиск по относительному составному имени "Группа / Название"
    p1 = storage.test_path("Информатика / М-25")
    assert p1.resolve() == f1.resolve()

    p2 = storage.test_path("ИСП-23 / МДК 05.02")
    assert p2.resolve() == f2.resolve()

    # 2. Проверяем fallback поиск по stem
    p1_fallback = storage.test_path("М-25")
    assert p1_fallback.resolve() == f1.resolve()

    # 3. Проверяем создание нового теста во вложенной папке
    new_nested = storage.test_path("Новый курс / Итоговый тест")
    assert new_nested.parent.name == "Новый курс"
    assert new_nested.name == "Итоговый_тест.txt" or new_nested.name == "Итоговый тест.txt"

    storage.set_custom_tests_dir(None)
