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


def compare_written_answer(student_ans: str, correct_ans: str) -> bool:
    """
    Сравнивает ответ студента с правильным ответом без учёта регистра.
    Для числовых ответов с плавающей точкой поддерживает как точки, так и запятые.
    """
    s_clean = student_ans.strip().lower()
    c_clean = correct_ans.strip().lower()
    
    if s_clean == c_clean:
        return True
        
    s_num_str = s_clean.replace(',', '.')
    c_num_str = c_clean.replace(',', '.')
    
    try:
        s_val = float(s_num_str)
        c_val = float(c_num_str)
        return s_val == c_val
    except ValueError:
        pass
        
    return False


def _finalize_question(question: Dict[str, Any]) -> Dict[str, Any]:
    """
    Финализирует словарь вопроса: собирает накопленные строки текста
    в одну строку, убирает лишние пробелы.
    """
    # Объединяем строки текста вопроса (могут быть многострочные)
    question['text'] = '\n'.join(question.get('_text_lines', [])).strip()
    question.pop('_text_lines', None)
    
    # Если в вопросе несколько правильных ответов, то по умолчанию выставляем множественный выбор
    # Но только если это не письменный вопрос
    if not question.get('written', False):
        correct_count = sum(1 for a in question.get('answers', []) if a.get('correct', False))
        if correct_count > 1:
            question['multiple'] = True
        
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
        if stripped.startswith('?'):
            # Финализируем предыдущий вопрос, если он был
            if current is not None:
                questions.append(_finalize_question(current))

            rest = stripped[1:].strip()
            
            # Проверяем старый формат: "?N" или "?N (С множественным выбором)" или "?N (Письменный ответ)"
            old_match = re.match(r'^(\d+)\s*(\(С множественным выбором\)|\(Письменный ответ\)|\(Письменно\))?$', rest, re.IGNORECASE)
            if old_match:
                q_number = int(old_match.group(1))
                marker = old_match.group(2)
                is_multiple = False
                is_written = False
                if marker:
                    if "множественн" in marker.lower():
                        is_multiple = True
                    elif "письмен" in marker.lower():
                        is_written = True
                text_part = ""
            else:
                # Новый формат
                is_multiple = False
                is_written = False
                mult_marker = "(С множественным выбором)"
                written_marker = "(Письменный ответ)"
                written_marker_alt = "(Письменно)"
                
                if rest.lower().startswith(mult_marker.lower()):
                    is_multiple = True
                    text_part = rest[len(mult_marker):].strip()
                elif rest.lower().startswith(written_marker.lower()):
                    is_written = True
                    text_part = rest[len(written_marker):].strip()
                elif rest.lower().startswith(written_marker_alt.lower()):
                    is_written = True
                    text_part = rest[len(written_marker_alt):].strip()
                else:
                    text_part = rest
                q_number = len(questions) + 1

            current = {
                'number': q_number,
                'multiple': is_multiple,
                'written': is_written,
                'image_data': None,
                'answers': [],
                '_text_lines': [text_part] if text_part else [],
            }
            continue

        # Если ещё не начался ни один вопрос — пропускаем строку
        if current is None:
            continue

        # Проверяем маркер изображения
        match_img = _IMAGE_RE.match(stripped)
        if match_img:
            image_filename = match_img.group(1).strip()
            # Защита от path traversal: @image:../../etc/passwd не должен сработать.
            # Разрешаем только пути, которые после нормализации остаются внутри test_dir.
            candidate = os.path.normpath(os.path.join(test_dir, image_filename))
            test_dir_norm = os.path.normpath(test_dir)
            if not (candidate == test_dir_norm or candidate.startswith(test_dir_norm + os.sep)):
                print(
                    f"[parser] Отклонён @image вне директории теста: {image_filename!r}"
                )
                current['image_data'] = None
            else:
                current['image_data'] = _read_image_as_base64(candidate)
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
    Для письменных вопросов ответы не отправляются вовсе, чтобы предотвратить читерство.
    """
    payload = []
    for q in questions:
        payload.append({
            'number': q['number'],
            'text': q['text'],
            'multiple': q['multiple'],
            'written': q.get('written', False),
            'image_data': q['image_data'],
            'answers': [a['text'] for a in q['answers']] if not q.get('written', False) else [],
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
        # Ищем ответ в словаре, поддерживая как числовые ключи, так и строковые
        selected = student_answers.get(q_num)
        if selected is None:
            selected = student_answers.get(str(q_num), [])

        if q.get('written', False):
            if not selected:
                continue
            student_text = selected[0] if isinstance(selected, list) else str(selected)
            is_correct = False
            for a in q['answers']:
                if a['correct'] and compare_written_answer(student_text, a['text']):
                    is_correct = True
                    break
            if is_correct:
                score += 1.0
            continue

        selected_set = set(str(s).strip() for s in selected)
        correct_set = set(str(a['text']).strip() for a in q['answers'] if a['correct'])
        wrong_selected = selected_set - correct_set

        if not correct_set:
            continue

        if q.get('multiple') and partial_multiple:
            correct_selected = selected_set & correct_set
            # Количество ВЕРНЫХ из ТЕХ, что должны быть выбраны, минус количество ОШИБОЧНЫХ
            # Делим на общее количество верных ответов в этом вопросе
            num_correct = len(correct_selected)
            num_wrong = len(wrong_selected)
            total_correct = len(correct_set)
            
            question_score = (num_correct - num_wrong) / total_correct
            score += max(0.0, min(1.0, question_score))
        else:
            # Для одиночного выбора или если частичный зачёт отключен
            # Нужно точное совпадение набора выбранных ответов с набором правильных
            if selected_set == correct_set and len(selected_set) > 0:
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
        
        # Чтение пороговых значений из настроек с безопасными дефолтами
        from PySide6.QtCore import QSettings
        settings = QSettings("EduTest", "Server")
        g5 = settings.value("grade_5_min", 90, type=int)
        g4 = settings.value("grade_4_min", 70, type=int)
        g3 = settings.value("grade_3_min", 50, type=int)
        
        if percent >= g5:
            return percent_str, "#10b981"
        elif percent >= g4:
            return percent_str, "#3b82f6"
        elif percent >= g3:
            return percent_str, "#f59e0b"
        else:
            return percent_str, "#ef4444"
    except Exception:
        return "—", "#64748b"
