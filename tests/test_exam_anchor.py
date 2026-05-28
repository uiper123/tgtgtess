"""
Регрессионный тест: читерство через переподключение (R-1).

Сценарий — см. SECURITY.md / chat audit. Кратко: студент в середине теста
выдёргивает Wi-Fi и снова подключается, чтобы сбросить серверный таймер.

Тест работает чисто на логике dict `attempts`/`exam_start_time` — без
поднятия Qt-окружения.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def fake_exam():
    return {
        "duration": 60,
        "max_attempts": 2,
        "attempts": {},
    }


def test_anchor_set_once_and_persists_across_reconnects(fake_exam):
    """Главный тест на R-1.

    Подключаемся первый раз -> exam_start_time зафиксирован.
    Симулируем ре-конн через 30 минут -> exam_start_time НЕ должен сброситься.
    """
    from server.main import ExamServer

    key = "ivanov"
    first = ExamServer._attempt_get_or_init_start_time(fake_exam, key)
    assert isinstance(first, datetime)

    rec = fake_exam["attempts"][key]
    rec["exam_start_time"] = first - timedelta(minutes=30)  # имитируем что прошло 30 мин

    again = ExamServer._attempt_get_or_init_start_time(fake_exam, key)
    assert again == first - timedelta(minutes=30), (
        "Якорь сбрасывается при повторном подключении — эксплойт R-1 жив!"
    )


def test_cheating_via_reconnect_no_longer_extends_time(fake_exam):
    """E2E-расчёт: симулируем что студент подключается на 55-й минуте
    повторно, и сервер должен видеть `elapsed=55min`, а не `0`.
    """
    from server.main import ExamServer

    key = "petrov"
    start = datetime.now() - timedelta(minutes=55)
    fake_exam["attempts"][key] = {"count": 0, "exam_start_time": start}

    # «Студент переподключается» — _handle_connect вызвал бы этот хелпер:
    anchor = ExamServer._attempt_get_or_init_start_time(fake_exam, key)
    elapsed_minutes = (datetime.now() - anchor).total_seconds() / 60

    assert 54 < elapsed_minutes < 56, f"elapsed={elapsed_minutes:.1f}, ожидали ~55"

    remaining = max(0, fake_exam["duration"] * 60 - int((datetime.now() - anchor).total_seconds()))
    assert remaining < 6 * 60, "Студент получил больше 6 минут — эксплойт работает!"


def test_int_legacy_attempts_migrate_to_dict(fake_exam):
    """Обратная совместимость: старые exam'ы с attempts[key]=int должны
    нормально мигрировать без потери счётчика."""
    from server.main import ExamServer

    fake_exam["attempts"]["sidorov"] = 1  # legacy int-формат
    assert ExamServer._attempt_count(fake_exam, "sidorov") == 1
    ExamServer._attempt_inc(fake_exam, "sidorov")
    assert ExamServer._attempt_count(fake_exam, "sidorov") == 2


def test_anchor_resets_after_attempt_finished(fake_exam):
    """После того как студент сдал работу — якорь должен обнулиться,
    чтобы на следующей попытке отсчёт начался заново."""
    from server.main import ExamServer

    key = "kuznetsov"
    first = ExamServer._attempt_get_or_init_start_time(fake_exam, key)

    ExamServer._attempt_reset_start_time(fake_exam, key)
    ExamServer._attempt_inc(fake_exam, key)

    second = ExamServer._attempt_get_or_init_start_time(fake_exam, key)
    assert second > first, "После reset якорь должен быть НОВЫЙ"
    assert ExamServer._attempt_count(fake_exam, key) == 1


def test_iso_string_anchor_is_parsed(fake_exam):
    """Если по какой-то причине exam_start_time сохранён как ISO-строка
    (например, после восстановления из JSON), хелпер должен его распарсить."""
    from server.main import ExamServer

    iso = (datetime.now() - timedelta(minutes=10)).isoformat()
    fake_exam["attempts"]["volkov"] = {"count": 0, "exam_start_time": iso}

    anchor = ExamServer._attempt_get_or_init_start_time(fake_exam, "volkov")
    assert isinstance(anchor, datetime)
    elapsed = (datetime.now() - anchor).total_seconds() / 60
    assert 9 < elapsed < 11
