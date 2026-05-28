"""Тесты на shared.parser.calculate_score — наиболее болезненная логика
(результат идёт в ведомость, нельзя позволить регресс)."""

from __future__ import annotations

import pytest

from shared.parser import calculate_score


def Q(number: int, answers: list[tuple[str, bool]], *, multiple=False, written=False):
    """Хелпер для построения вопросов в тестах."""
    return {
        "number": number,
        "text": f"Q{number}",
        "multiple": multiple,
        "written": written,
        "image_data": None,
        "answers": [{"text": a, "correct": c} for a, c in answers],
    }


# ---------------------------------------------------------------------------
# Одиночный выбор
# ---------------------------------------------------------------------------


def test_single_choice_correct():
    qs = [Q(1, [("A", True), ("B", False)])]
    assert calculate_score(qs, {1: ["A"]}) == "1/1"


def test_single_choice_wrong():
    qs = [Q(1, [("A", True), ("B", False)])]
    assert calculate_score(qs, {1: ["B"]}) == "0/1"


def test_unanswered_question_scores_zero():
    qs = [Q(1, [("A", True), ("B", False)])]
    assert calculate_score(qs, {}) == "0/1"


def test_string_keys_also_work():
    # protocol сериализует int → str через JSON; убедимся, что
    # calculate_score устойчив к этому.
    qs = [Q(1, [("A", True), ("B", False)])]
    assert calculate_score(qs, {"1": ["A"]}) == "1/1"


# ---------------------------------------------------------------------------
# Множественный выбор — частичный зачёт
# ---------------------------------------------------------------------------


def test_multi_choice_all_correct():
    qs = [Q(1, [("A", True), ("B", True), ("C", False)], multiple=True)]
    assert calculate_score(qs, {1: ["A", "B"]}) == "1/1"


def test_multi_choice_half_correct_no_wrong():
    qs = [Q(1, [("A", True), ("B", True), ("C", False)], multiple=True)]
    # Выбран 1 из 2 правильных, без неправильных → 0.5/1
    assert calculate_score(qs, {1: ["A"]}) == "0.5/1"


def test_multi_choice_one_correct_one_wrong():
    qs = [Q(1, [("A", True), ("B", True), ("C", False)], multiple=True)]
    # 1 правильный − 1 неправильный = 0 баллов
    assert calculate_score(qs, {1: ["A", "C"]}) == "0/1"


def test_multi_choice_score_never_negative():
    qs = [Q(1, [("A", True), ("B", True), ("C", False), ("D", False)], multiple=True)]
    # 0 правильных − 2 неправильных = −0.5 → клип в 0
    assert calculate_score(qs, {1: ["C", "D"]}) == "0/1"


def test_multi_choice_strict_mode():
    qs = [Q(1, [("A", True), ("B", True), ("C", False)], multiple=True)]
    # При partial_multiple=False работает «всё или ничего»
    assert calculate_score(qs, {1: ["A"]}, partial_multiple=False) == "0/1"
    assert calculate_score(qs, {1: ["A", "B"]}, partial_multiple=False) == "1/1"


# ---------------------------------------------------------------------------
# Письменные ответы
# ---------------------------------------------------------------------------


def test_written_correct_exact():
    qs = [Q(1, [("Москва", True)], written=True)]
    assert calculate_score(qs, {1: ["москва"]}) == "1/1"


def test_written_correct_alternate():
    qs = [Q(1, [("Москва", True), ("Moscow", True)], written=True)]
    assert calculate_score(qs, {1: ["MOSCOW"]}) == "1/1"


def test_written_empty_answer():
    qs = [Q(1, [("Москва", True)], written=True)]
    assert calculate_score(qs, {1: [""]}) == "0/1"


def test_written_numeric_comma():
    qs = [Q(1, [("0.5", True)], written=True)]
    assert calculate_score(qs, {1: ["0,5"]}) == "1/1"


# ---------------------------------------------------------------------------
# Смешанный тест
# ---------------------------------------------------------------------------


def test_mixed_test():
    qs = [
        Q(1, [("A", True), ("B", False)]),                  # single
        Q(2, [("X", True), ("Y", True), ("Z", False)], multiple=True),
        Q(3, [("Hello", True)], written=True),
    ]
    answers = {1: ["A"], 2: ["X", "Y"], 3: ["hello"]}
    assert calculate_score(qs, answers) == "3/3"


def test_score_format_strips_trailing_zeros():
    # 0.5 не должен превратиться в "0.50/2"
    qs = [
        Q(1, [("A", True), ("B", True)], multiple=True),
        Q(2, [("A", True), ("B", False)]),
    ]
    # На первом вопросе выбран 1 из 2 → 0.5; на втором — правильно.
    assert calculate_score(qs, {1: ["A"], 2: ["A"]}) == "1.5/2"
