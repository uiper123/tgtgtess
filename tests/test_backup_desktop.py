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
