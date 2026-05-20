"""
shared/parser.py — Нативный парсер TXT-файлов тестов и кодировщик картинок в Base64.

Формат входного файла:
  ?N                          — начало вопроса N (одиночный выбор)
  ?N (С множественным выбором) — начало вопроса N (множественный выбор)
  @image:имя_файла.png        — маркер изображения (ищется рядом с файлом теста)
  +Текст                      — правильный вариант ответа
  -Текст                      — неправильный вариант ответа

Результат: список словарей вида:
  {
      "number": int,
      "text": str,
      "multiple": bool,
      "image_data": str | None,   # Base64 строка или None
      "answers": [
          {"text": str, "correct": bool},
          ...
      ]
  }
"""

import os
import re
import base64
from typing import List, Dict, Any, Optional


class TestQuestionsList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = "Итоговое тестирование"
        self.section = "Раздел: Основная часть"


# Регулярные выражения для метаданных теста
_TITLE_RE = re.compile(r'^@title:\s*(.+)\s*$', re.IGNORECASE)
_SECTION_RE = re.compile(r'^@section:\s*(.+)\s*$', re.IGNORECASE)

# Регулярное выражение для строки начала вопроса: ?N или ?N (С множественным выбором)
_QUESTION_RE = re.compile(
    r'^\?(\d+)\s*(\(С множественным выбором\))?\s*$',
    re.IGNORECASE
)

# Регулярное выражение для маркера изображения: @image:имя_файла
_IMAGE_RE = re.compile(r'^@image:\s*(.+)\s*$', re.IGNORECASE)

# Регулярное выражение для base64 изображения: @image_base64:строка
_IMAGE_BASE64_RE = re.compile(r'^@image_base64:\s*(.+)\s*$', re.IGNORECASE)


def _read_image_as_base64(image_path: str) -> Optional[str]:
    """
    Считывает файл изображения и возвращает его содержимое в виде Base64-строки.
    Если файл не найден или не может быть прочитан, возвращает None.
    """
    if not os.path.isfile(image_path):
        print(f"[parser] Предупреждение: файл изображения не найден: {image_path}")
        return None
    try:
        with open(image_path, 'rb') as f:
            raw = f.read()
        return base64.b64encode(raw).decode('utf-8')
    except (IOError, OSError) as exc:
        print(f"[parser] Ошибка чтения изображения {image_path}: {exc}")
        return None


def _finalize_question(question: Dict[str, Any]) -> Dict[str, Any]:
    """
    Финализирует словарь вопроса: собирает накопленные строки текста
    в одну строку, убирает лишние пробелы.
    """
    # Объединяем строки текста вопроса (могут быть многострочные)
    question['text'] = '\n'.join(question.get('_text_lines', [])).strip()
    question.pop('_text_lines', None)
    return question


def parse_test_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Парсит TXT-файл теста и возвращает упорядоченный список вопросов.

    Args:
        filepath: Абсолютный или относительный путь к .txt файлу теста.

    Returns:
        Список словарей-вопросов (см. описание модуля).

    Raises:
        FileNotFoundError: если файл теста не существует.
        ValueError: если файл не содержит ни одного вопроса.
    """
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Файл теста не найден: {filepath}")

    test_dir = os.path.dirname(os.path.abspath(filepath))

    # Пытаемся прочитать файл в UTF-8, если не получается — в CP1251 (Windows)
    content: str = ''
    for encoding in ('utf-8', 'cp1251', 'latin-1'):
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    lines = content.splitlines()
    questions = TestQuestionsList()
    current: Optional[Dict[str, Any]] = None

    for line in lines:
        stripped = line.strip()

        # Пустая строка — пропускаем
        if not stripped:
            continue

        # Сначала проверяем метаданные заголовков (если еще не начался первый вопрос)
        if current is None:
            match_t = _TITLE_RE.match(stripped)
            if match_t:
                questions.title = match_t.group(1).strip()
                continue
            match_s = _SECTION_RE.match(stripped)
            if match_s:
                questions.section = match_s.group(1).strip()
                continue

        # Проверяем, начинается ли новый вопрос
        match_q = _QUESTION_RE.match(stripped)
        if match_q:
            # Финализируем предыдущий вопрос, если он был
            if current is not None:
                questions.append(_finalize_question(current))

            q_number = int(match_q.group(1))
            is_multiple = match_q.group(2) is not None

            current = {
                'number': q_number,
                'multiple': is_multiple,
                'image_data': None,
                'answers': [],
                '_text_lines': [],  # временный накопитель строк текста
            }
            continue

        # Если ещё не начался ни один вопрос — пропускаем строку
        if current is None:
            continue

        # Проверяем маркер изображения
        match_img = _IMAGE_RE.match(stripped)
        if match_img:
            image_filename = match_img.group(1).strip()
            image_path = os.path.join(test_dir, image_filename)
            current['image_data'] = _read_image_as_base64(image_path)
            continue

        # Проверяем маркер base64 изображения
        match_img_b64 = _IMAGE_BASE64_RE.match(stripped)
        if match_img_b64:
            current['image_data'] = match_img_b64.group(1).strip()
            continue

        # Проверяем вариант ответа: правильный (+) или неправильный (-)
        if stripped.startswith('+'):
            answer_text = stripped[1:].strip()
            current['answers'].append({'text': answer_text, 'correct': True})
            continue

        if stripped.startswith('-'):
            answer_text = stripped[1:].strip()
            current['answers'].append({'text': answer_text, 'correct': False})
            continue

        # Всё остальное — текст вопроса (может быть многострочным)
        current['_text_lines'].append(stripped)

    # Финализируем последний вопрос
    if current is not None:
        questions.append(_finalize_question(current))

    if not questions:
        raise ValueError(f"Файл '{filepath}' не содержит ни одного вопроса.")

    return questions


# ---------------------------------------------------------------------------
# Утилиты для подготовки данных к сетевой передаче
# ---------------------------------------------------------------------------

def questions_to_network_payload(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Преобразует список вопросов в формат, пригодный для отправки клиенту
    по сети (без поля 'correct' в ответах — студент не должен его видеть).
    """
    payload = []
    for q in questions:
        payload.append({
            'number': q['number'],
            'text': q['text'],
            'multiple': q['multiple'],
            'image_data': q['image_data'],
            'answers': [a['text'] for a in q['answers']],
        })
    return payload


def calculate_score(
    questions: List[Dict[str, Any]],
    student_answers: Dict[int, List[str]],
    partial_multiple: bool = True
) -> str:
    """
    Подсчитывает оценку студента.

    Args:
        questions: Полный список вопросов (с правильными ответами).
        student_answers: Словарь {номер_вопроса: [выбранные_ответы]}.

    Returns:
        Строка вида 'X/Y' (набранные баллы / максимум).
    """
    total = len(questions)
    score = 0.0

    for q in questions:
        q_num = q['number']
        selected = set(student_answers.get(q_num, []))
        correct_set = set(a['text'] for a in q['answers'] if a['correct'])
        wrong_selected = selected - correct_set

        if not correct_set:
            continue
        if q.get('multiple') and partial_multiple:
            correct_selected = selected & correct_set
            question_score = (len(correct_selected) - len(wrong_selected)) / len(correct_set)
            score += max(0.0, min(1.0, question_score))
        elif selected == correct_set:
            score += 1.0

    score_str = f"{score:.2f}".rstrip('0').rstrip('.')
    return f"{score_str}/{total}"


def get_grade_details(score_str: str) -> tuple:
    """
    Рассчитывает процент прохождения на основе строки результата 'X/Y'
    и возвращает кортеж (процент_строка, hex_цвет).
    """
    try:
        parts = score_str.split('/')
        correct = float(parts[0])
        total = float(parts[1])
        if total == 0:
            return "0%", "#ef4444"
        percent = (correct / total) * 100
        percent_str = f"{int(percent)}%"
        if percent >= 90:
            return percent_str, "#10b981"
        elif percent >= 70:
            return percent_str, "#3b82f6"
        elif percent >= 50:
            return percent_str, "#f59e0b"
        else:
            return percent_str, "#ef4444"
    except Exception:
        return "—", "#64748b"
