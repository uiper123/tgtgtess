"""Тесты на shared/parser.py — pure Python, без Qt/UI."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from shared.parser import (
    compare_written_answer,
    parse_test_file,
    questions_to_network_payload,
)


# ---------------------------------------------------------------------------
# Базовый парсинг
# ---------------------------------------------------------------------------


def test_parse_simple_single_choice(tmp_test_file):
    path = tmp_test_file(
        "?1\n"
        "Какой протокол используется для безопасной передачи?\n"
        "+HTTPS\n"
        "-HTML\n"
        "-FTP\n"
    )
    questions = parse_test_file(path)

    assert len(questions) == 1
    q = questions[0]
    assert q["number"] == 1
    assert q["multiple"] is False
    assert q["written"] is False
    assert "безопасной передачи" in q["text"]
    assert q["image_data"] is None
    assert [a["text"] for a in q["answers"]] == ["HTTPS", "HTML", "FTP"]
    assert [a["correct"] for a in q["answers"]] == [True, False, False]


def test_multiple_choice_marker_explicit(tmp_test_file):
    path = tmp_test_file(
        "?1 (С множественным выбором)\n"
        "Выберите языки программирования:\n"
        "+Python\n"
        "+JavaScript\n"
        "-HTML\n"
    )
    [q] = parse_test_file(path)
    assert q["multiple"] is True
    assert q["written"] is False
    correct = [a["text"] for a in q["answers"] if a["correct"]]
    assert correct == ["Python", "JavaScript"]


def test_multiple_choice_auto_detected_when_multiple_pluses(tmp_test_file):
    # Без явного маркера, но с двумя «+» — должно автоматом стать multiple.
    path = tmp_test_file(
        "?1\n"
        "Кто относится к языкам со статической типизацией?\n"
        "+Java\n"
        "+C++\n"
        "-Python\n"
    )
    [q] = parse_test_file(path)
    assert q["multiple"] is True


def test_written_answer_marker(tmp_test_file):
    path = tmp_test_file(
        "?1 (Письменный ответ)\n"
        "Назовите столицу Франции\n"
        "+Париж\n"
        "+Paris\n"
    )
    [q] = parse_test_file(path)
    assert q["written"] is True
    # Письменный вопрос НЕ конвертируется в multiple даже при нескольких +.
    assert q["multiple"] is False


def test_metadata_title_and_section(tmp_test_file):
    path = tmp_test_file(
        "@title: Контрольная по сетям\n"
        "@section: Раздел: Транспортный уровень\n"
        "?1\nЧто такое TCP?\n+Протокол транспортного уровня\n-СУБД\n"
    )
    questions = parse_test_file(path)
    assert questions.title == "Контрольная по сетям"
    assert questions.section == "Раздел: Транспортный уровень"


def test_multiline_question_text(tmp_test_file):
    path = tmp_test_file(
        "?1\n"
        "Строка 1\n"
        "Строка 2\n"
        "Строка 3\n"
        "+Да\n"
        "-Нет\n"
    )
    [q] = parse_test_file(path)
    assert q["text"].splitlines() == ["Строка 1", "Строка 2", "Строка 3"]


def test_empty_file_raises(tmp_test_file):
    path = tmp_test_file("")
    with pytest.raises(ValueError):
        parse_test_file(path)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_test_file(str(tmp_path / "nope.txt"))


def test_cp1251_encoding_fallback(tmp_path: Path):
    # Сохраняем тест в cp1251 — типичный кейс для Windows-преподавателей.
    p = tmp_path / "win.txt"
    content = "?1\nКирилличный вопрос?\n+Да\n-Нет\n"
    p.write_bytes(content.encode("cp1251"))
    [q] = parse_test_file(str(p))
    assert "Кирилличный" in q["text"]


# ---------------------------------------------------------------------------
# Изображения и path-traversal
# ---------------------------------------------------------------------------


def test_image_loaded_when_present(tmp_path: Path):
    img_path = tmp_path / "pic.png"
    img_path.write_bytes(b"\x89PNGfake")
    test_path = tmp_path / "t.txt"
    test_path.write_text("?1\n@image:pic.png\nВопрос?\n+Да\n-Нет\n", encoding="utf-8")
    [q] = parse_test_file(str(test_path))
    assert q["image_data"] == base64.b64encode(b"\x89PNGfake").decode()


def test_image_base64_inline(tmp_test_file):
    encoded = base64.b64encode(b"hello").decode()
    path = tmp_test_file(
        f"?1\n@image_base64:{encoded}\nВопрос?\n+Да\n-Нет\n"
    )
    [q] = parse_test_file(path)
    assert q["image_data"] == encoded


def test_image_path_traversal_blocked(tmp_path: Path):
    # «Враждебный» секрет вне директории теста.
    secret = tmp_path / "secret.png"
    secret.write_bytes(b"TOP_SECRET")

    # Сам тест — в подкаталоге, @image пытается выскочить наверх.
    sub = tmp_path / "tests-folder"
    sub.mkdir()
    test_path = sub / "t.txt"
    test_path.write_text(
        "?1\n@image:../secret.png\nЧто-то?\n+Да\n-Нет\n", encoding="utf-8"
    )

    [q] = parse_test_file(str(test_path))
    # Главное: содержимое secret.png НЕ должно утечь в сетевую полезную нагрузку.
    assert q["image_data"] is None
    assert base64.b64encode(b"TOP_SECRET").decode() not in (q["image_data"] or "")


def test_image_missing_does_not_crash(tmp_test_file):
    path = tmp_test_file("?1\n@image:no-such.png\nQ\n+Да\n-Нет\n")
    [q] = parse_test_file(path)
    assert q["image_data"] is None


# ---------------------------------------------------------------------------
# questions_to_network_payload — самое важное: не утекают correct-флаги
# и письменные ответы.
# ---------------------------------------------------------------------------


def test_network_payload_strips_correctness(tmp_test_file):
    path = tmp_test_file(
        "?1\nQ?\n+Да\n-Нет\n"
        "?2 (Письменный ответ)\nСтолица?\n+Москва\n+Moscow\n"
    )
    questions = parse_test_file(path)
    payload = questions_to_network_payload(questions)

    # У обычного вопроса варианты сохранены, но без correct-флага.
    assert payload[0]["answers"] == ["Да", "Нет"]
    assert "correct" not in str(payload[0]["answers"])

    # У письменного вопроса ответы НЕ должны утекать к студенту.
    assert payload[1]["written"] is True
    assert payload[1]["answers"] == []


# ---------------------------------------------------------------------------
# compare_written_answer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "student, correct, expected",
    [
        ("Москва", "москва", True),
        ("  Москва  ", "Москва", True),
        ("0.5", "0,5", True),         # точка/запятая в числах
        ("1", "1.0", True),
        ("Москв", "Москва", False),
        ("Питер", "Москва", False),
        ("", "Москва", False),
    ],
)
def test_compare_written_answer(student, correct, expected):
    assert compare_written_answer(student, correct) is expected
