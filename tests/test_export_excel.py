"""
Тесты экспорта результатов в Excel (.xlsx) и расчета 5-балльной шкалы оценок.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

openpyxl = pytest.importorskip("openpyxl")

from server.export_excel import calculate_grade_5, export_results_to_xlsx, parse_score_percent


def test_calculate_grade_5():
    assert calculate_grade_5(95, g5=90, g4=70, g3=50) == (5, "Отлично")
    assert calculate_grade_5(90, g5=90, g4=70, g3=50) == (5, "Отлично")
    assert calculate_grade_5(89.9, g5=90, g4=70, g3=50) == (4, "Хорошо")
    assert calculate_grade_5(70, g5=90, g4=70, g3=50) == (4, "Хорошо")
    assert calculate_grade_5(69.9, g5=90, g4=70, g3=50) == (3, "Удовлетворительно")
    assert calculate_grade_5(50, g5=90, g4=70, g3=50) == (3, "Удовлетворительно")
    assert calculate_grade_5(49.9, g5=90, g4=70, g3=50) == (2, "Неудовлетворительно")
    assert calculate_grade_5(0, g5=90, g4=70, g3=50) == (2, "Неудовлетворительно")


def test_parse_score_percent():
    assert parse_score_percent("18/20") == 90.0
    assert parse_score_percent("10/20") == 50.0
    assert parse_score_percent("85%") == 85.0
    assert parse_score_percent(75) == 75.0
    assert parse_score_percent("—") == 0.0
    assert parse_score_percent("") == 0.0


def test_export_results_to_xlsx(tmp_path: Path):
    sample_results = [
        {
            "name": "Иванов Иван Иванович",
            "group": "ИСП-311",
            "test_name": "Компьютерные сети",
            "score": "19/20",
            "timestamp": "2026-08-28 12:00:00",
        },
        {
            "name": "Петров Петр Петрович",
            "group": "ИСП-311",
            "test_name": "Компьютерные сети",
            "score": "15/20",
            "timestamp": "2026-08-28 12:01:00",
        },
        {
            "name": "Сидоров Сидор Сидорович",
            "group": "ИСП-311",
            "test_name": "Компьютерные сети",
            "score": "11/20",
            "timestamp": "2026-08-28 12:02:00",
        },
        {
            "name": "Кузнецов Алексей Сергеевич",
            "group": "ИСП-311",
            "test_name": "Компьютерные сети",
            "score": "7/20",
            "timestamp": "2026-08-28 12:03:00",
        },
    ]

    xlsx_file = tmp_path / "test_results.xlsx"
    saved_path = export_results_to_xlsx(
        sample_results,
        xlsx_file,
        title="Ведомость экзаменационной группы",
        group_name="ИСП-311",
        test_title="Компьютерные сети",
    )

    assert os.path.exists(saved_path)

    wb = openpyxl.load_workbook(saved_path)
    ws = wb.active
    assert ws.title == "Результаты"

    # Заголовок
    assert "Ведомость экзаменационной группы" in ws["A1"].value
    assert "ИСП-311" in ws["A2"].value

    # Заголовки таблицы
    headers = [ws.cell(row=4, column=c).value for c in range(1, 9)]
    assert "ФИО студента" in headers
    assert "Оценка" in headers
    assert "Процент" in headers

    # Проверяем строки студентов и рассчитанные оценки
    assert ws.cell(row=5, column=2).value == "Иванов Иван Иванович"
    assert ws.cell(row=5, column=6).value == "95%"
    assert ws.cell(row=5, column=7).value == 5

    assert ws.cell(row=6, column=2).value == "Петров Петр Петрович"
    assert ws.cell(row=6, column=6).value == "75%"
    assert ws.cell(row=6, column=7).value == 4

    assert ws.cell(row=7, column=2).value == "Сидоров Сидор Сидорович"
    assert ws.cell(row=7, column=6).value == "55%"
    assert ws.cell(row=7, column=7).value == 3

    assert ws.cell(row=8, column=2).value == "Кузнецов Алексей Сергеевич"
    assert ws.cell(row=8, column=6).value == "35%"
    assert ws.cell(row=8, column=7).value == 2
