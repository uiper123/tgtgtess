"""
Тесты сохранения резервных копий (бэкапов) на Рабочий стол и в гостевом режиме.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

try:
    import PySide6.QtWidgets
    _ = PySide6.QtWidgets
except ImportError:
    pytest.skip("libEGL missing — skipping QtWidgets-dependent tests", allow_module_level=True)

from client.main import get_student_backup_dir, save_student_final_backup, xor_decrypt


def test_get_student_backup_dir():
    backup_dir = get_student_backup_dir()
    assert backup_dir is not None
    assert os.path.exists(backup_dir)
    assert os.path.isdir(backup_dir)

    # Проверяем возможность записи
    test_file = os.path.join(backup_dir, ".test_write.tmp")
    with open(test_file, "wb") as f:
        f.write(b"ok")
    assert os.path.exists(test_file)
    os.remove(test_file)


def test_save_student_final_backup():
    name = "Петров Пётр"
    group = "ИСП-201"
    score = "15/20"
    answers = {0: ["1"], 1: ["0", "2"]}
    test_name = "Тест по базам данных"

    filepath = save_student_final_backup(name, group, score, answers, test_name)
    assert filepath is not None
    assert os.path.exists(filepath)
    assert "Бэкап_ИСП-201_Петров_Пётр.log" in filepath

    # Читаем и расшифровываем файл
    with open(filepath, "rb") as f:
        encrypted = f.read()

    decrypted = xor_decrypt(encrypted)
    data = json.loads(decrypted.decode("utf-8"))

    assert data["name"] == name
    assert data["group"] == group
    assert data["score"] == score
    assert data["answers"]["0"] == ["1"] or data["answers"][0] == ["1"]
    assert data["test_name"] == test_name

    # Очищаем за собой тестовый файл
    try:
        os.remove(filepath)
    except OSError:
        pass


def test_save_and_load_rich_student_backup_with_questions():
    name = "Иванов Иван"
    group = "ИС-21"
    score = "2/2"
    answers = {0: ["Ответ А"], 1: ["Ответ Б"]}
    test_name = "Итоговый экзамен"
    title = "Тестирование по программированию"
    section = "Модуль 1"
    duration = 45
    sample_questions = [
        {"number": 1, "text": "Вопрос 1", "type": "single", "answers": [{"text": "Ответ А", "correct": True}, {"text": "Ответ Б", "correct": False}]},
        {"number": 2, "text": "Вопрос 2", "type": "single", "answers": [{"text": "Ответ А", "correct": False}, {"text": "Ответ Б", "correct": True}]},
    ]

    filepath = save_student_final_backup(
        name,
        group,
        score,
        answers,
        test_name=test_name,
        questions=sample_questions,
        test_title=title,
        test_section=section,
        duration=duration,
    )
    assert filepath is not None
    assert os.path.exists(filepath)

    # Расшифровываем
    with open(filepath, "rb") as f:
        raw_enc = f.read()

    data = json.loads(xor_decrypt(raw_enc).decode("utf-8"))
    assert data["version"] == 2
    assert data["name"] == name
    assert data["group"] == group
    assert data["score"] == "2/2"
    assert data["test_title"] == title
    assert data["test_section"] == section
    assert data["duration"] == duration
    assert len(data["questions"]) == 2
    assert data["questions"][0]["text"] == "Вопрос 1"

    # Очистка
    try:
        os.remove(filepath)
    except OSError:
        pass
