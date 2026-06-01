import os

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from shared.widgets import StyledComboBox

try:
    from shared.parser import get_grade_details
    from shared.styles import get_scaled_qss

    from .styles import GLOBAL_QSS
except ImportError:
    from styles import GLOBAL_QSS

    from shared.parser import get_grade_details
    from shared.styles import get_scaled_qss

def apply_dialog_scaling(dialog, parent, base_w, base_h):
    scale_factor = 1.0
    if parent and hasattr(parent, "_settings"):
        saved_scale = parent._settings.value("ui_scale", "100%")
        if saved_scale == "80%":
            scale_factor = 0.8
        elif saved_scale == "125%":
            scale_factor = 1.25
        elif saved_scale == "150%":
            scale_factor = 1.5
        elif saved_scale == "175%":
            scale_factor = 1.75
        elif saved_scale == "200%":
            scale_factor = 2.0

    dialog.resize(int(base_w * scale_factor), int(base_h * scale_factor))
    from shared.styles import inject_icon_paths
    dialog.setStyleSheet(inject_icon_paths(get_scaled_qss(GLOBAL_QSS, scale_factor)))


# ---------------------------------------------------------------------------
# Shared label helpers — keep dialogs visually consistent.
# Returned labels carry transparent background + no border so they sit
# cleanly on any card or dialog surface.
# ---------------------------------------------------------------------------
def _title_label(text: str, size: int = 18) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: {size}px; font-weight: 600; color: #1c1917;"
        " border: none; background: transparent;"
    )
    return lbl


def _section_label(text: str, size: int = 13) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: {size}px; font-weight: 600; color: #44403c;"
        " border: none; background: transparent;"
    )
    return lbl


def _muted_label(text: str, size: int = 12) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"font-size: {size}px; color: #78716c;"
        " border: none; background: transparent;"
    )
    return lbl


class StudentAnswersDialog(QDialog):
    def __init__(self, student, questions, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ответы студента: {student.name}")
        apply_dialog_scaling(self, parent, 700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = _title_label(f"Ответы студента: {student.name} ({student.group})")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #e7e5e4; border-radius: 8px; background-color: #ffffff; }"
        )

        scroll_content = QWidget()
        scroll_content.setObjectName("scroll_content")
        scroll_content.setStyleSheet("#scroll_content { background-color: #ffffff; }")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(16, 16, 16, 16)
        scroll_layout.setAlignment(Qt.AlignTop)

        if not student.answers:
            no_ans = _muted_label("Студент ещё не отправил ответы.", size=13)
            scroll_layout.addWidget(no_ans)
        else:
            for idx, q in enumerate(questions):
                q_num = q.get('number', idx + 1)
                student_ans = student.answers.get(q_num, [])
                correct_answers = [ans['text'] for ans in q.get('answers', []) if ans.get('correct')]

                if q.get('written'):
                    student_text = student_ans[0] if student_ans else ""
                    from shared.parser import compare_written_answer
                    is_correct = any(compare_written_answer(student_text, ans_text) for ans_text in correct_answers)
                    q_score_val = 1.0 if is_correct else 0.0
                else:
                    from shared.parser import calculate_score
                    single_q_score_str = calculate_score([q], {q_num: student_ans}, partial_multiple=True)
                    try:
                        q_score_val = float(single_q_score_str.split('/')[0])
                    except:
                        q_score_val = 0.0
                    is_correct = (q_score_val >= 1.0)

                q_card = QFrame()
                q_card.setStyleSheet(
                    "background-color: #fafaf9; border: 1px solid #e7e5e4;"
                    " border-radius: 10px; padding: 12px;"
                )
                card_lay = QVBoxLayout(q_card)
                card_lay.setSpacing(6)

                header = QHBoxLayout()
                q_lbl = QLabel(f"Вопрос {q_num}: {q.get('text', '')}")
                q_lbl.setWordWrap(True)
                q_lbl.setStyleSheet(
                    "font-size: 13px; font-weight: 600; color: #292524;"
                    " border: none; background: transparent;"
                )
                header.addWidget(q_lbl, 1)

                badge = QLabel()
                badge_base = (
                    "font-size: 11px; font-weight: 600; padding: 3px 10px;"
                    " border-radius: 999px; border: none;"
                )
                if q_score_val >= 1.0:
                    badge.setText(f"Верно · {q_score_val}")
                    badge.setStyleSheet(
                        badge_base + " background-color: #dcfce7; color: #14532d;"
                    )
                elif q_score_val > 0:
                    badge.setText(f"Частично · {q_score_val}")
                    badge.setStyleSheet(
                        badge_base + " background-color: #fef3c7; color: #92400e;"
                    )
                else:
                    badge.setText(f"Неверно · {q_score_val}")
                    badge.setStyleSheet(
                        badge_base + " background-color: #fee2e2; color: #991b1b;"
                    )
                header.addWidget(badge)
                card_lay.addLayout(header)

                if q.get('written'):
                    sel_lbl = QLabel(f"Ответ студента: {student_ans[0] if student_ans else '[нет ответа]'}")
                elif q.get('matching'):
                    sel_lbl = QLabel(f"Сопоставлено:\n" + "\n".join(f"• {pa}" for pa in student_ans) if student_ans else "Сопоставлено: [нет ответа]")
                else:
                    sel_lbl = QLabel(f"Выбрано: {', '.join(student_ans) if student_ans else '[нет ответа]'}")
                sel_lbl.setWordWrap(True)
                sel_lbl.setStyleSheet(
                    "font-size: 12px; color: #57534e; border: none; background: transparent;"
                )
                card_lay.addWidget(sel_lbl)

                if q.get('written'):
                    cor_lbl = QLabel(f"Правильные варианты: {', '.join(correct_answers)}")
                elif q.get('matching'):
                    correct_pairs_list = [f"• {a.get('key')} = {a.get('value')}" for a in q.get('answers', [])]
                    cor_lbl = QLabel(f"Правильные пары соответствия:\n" + "\n".join(correct_pairs_list))
                else:
                    cor_lbl = QLabel(f"Правильный ответ: {', '.join(correct_answers)}")
                cor_lbl.setWordWrap(True)
                cor_lbl.setStyleSheet(
                    "font-size: 12px; color: #15803d; font-weight: 500;"
                    " border: none; background: transparent;"
                )
                card_lay.addWidget(cor_lbl)

                scroll_layout.addWidget(q_card)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        close_btn = QPushButton("Закрыть")
        close_btn.setProperty("class", "primaryBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, 0, Qt.AlignRight)


class EditQuestionDialog(QDialog):
    def __init__(self, question=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование вопроса" if question else "Создание вопроса")
        apply_dialog_scaling(self, parent, 650, 600)

        self.question = question if question else {
            "number": 1,
            "text": "",
            "multiple": False,
            "written": False,
            "answers": [],
            "image_data": None
        }

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        lbl1 = _section_label("Текст вопроса")
        layout.addWidget(lbl1)

        self.q_text_input = QTextEdit()
        self.q_text_input.setPlaceholderText("Введите текст вопроса...")
        self.q_text_input.setPlainText(self.question.get("text", ""))
        self.q_text_input.setMaximumHeight(80)
        self.q_text_input.setStyleSheet(
            "QTextEdit { background-color: #ffffff; border: 1px solid #e7e5e4;"
            " border-radius: 8px; padding: 8px; font-size: 13px; color: #292524; }"
            "QTextEdit:focus { border: 1px solid #2563eb; }"
        )
        layout.addWidget(self.q_text_input)

        type_lay = QHBoxLayout()
        type_lbl = _section_label("Тип вопроса")
        type_lay.addWidget(type_lbl)

        self.q_type_combo = StyledComboBox()
        self.q_type_combo.addItems([
            "Одиночный выбор",
            "Множественный выбор",
            "Письменный ответ",
            "Соответствие",
            "Порядок",
            "Пропуски в тексте"
        ])

        if self.question.get("written", False):
            self.q_type_combo.setCurrentIndex(2)
        elif self.question.get("multiple", False):
            self.q_type_combo.setCurrentIndex(1)
        elif self.question.get("matching", False):
            self.q_type_combo.setCurrentIndex(3)
        elif self.question.get("ordering", False):
            self.q_type_combo.setCurrentIndex(4)
        elif self.question.get("blanks", False):
            self.q_type_combo.setCurrentIndex(5)
        else:
            self.q_type_combo.setCurrentIndex(0)


        self.type_hint_lbl = QLabel("")
        self.type_hint_lbl.setStyleSheet("font-size: 13px; color: #8b5cf6; font-weight: 500;")
        self.type_hint_lbl.setWordWrap(True)
        layout.addWidget(self.type_hint_lbl)

        type_lay.addWidget(self.q_type_combo)
        type_lay.addStretch()
        layout.addLayout(type_lay)

        img_layout = QHBoxLayout()
        self.img_status = _muted_label(
            "Изображение отсутствует" if not self.question.get("image_data") else "Изображение прикреплено"
        )
        img_layout.addWidget(self.img_status)

        self.add_img_btn = QPushButton("Выбрать изображение")
        self.add_img_btn.setProperty("class", "secondaryBtn")
        self.add_img_btn.setCursor(Qt.PointingHandCursor)
        self.add_img_btn.clicked.connect(self._select_image)
        img_layout.addWidget(self.add_img_btn)

        self.remove_img_btn = QPushButton("Удалить")
        self.remove_img_btn.setProperty("class", "dangerBtn")
        self.remove_img_btn.setCursor(Qt.PointingHandCursor)
        self.remove_img_btn.clicked.connect(self._remove_image)
        if not self.question.get("image_data"):
            self.remove_img_btn.hide()
        img_layout.addWidget(self.remove_img_btn)

        layout.addLayout(img_layout)

        self.ans_title_lbl = _section_label("Варианты ответов")
        layout.addWidget(self.ans_title_lbl)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #e7e5e4; border-radius: 8px; background-color: #ffffff; }"
            "QScrollArea > QWidget > QWidget { background-color: #ffffff; }"
        )
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scroll_content")
        self.scroll_content.setStyleSheet("#scroll_content { background-color: #ffffff; }")
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setSpacing(8)
        self.scroll_content_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_content_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.add_ans_btn = QPushButton("Добавить вариант ответа")
        self.add_ans_btn.setProperty("class", "secondaryBtn")
        self.add_ans_btn.setCursor(Qt.PointingHandCursor)
        self.add_ans_btn.clicked.connect(self._add_answer_row)
        layout.addWidget(self.add_ans_btn)

        # Bottom Buttons
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setProperty("class", "secondaryBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(cancel_btn)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setProperty("class", "primaryBtn")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._save_changes)
        btn_lay.addWidget(self.save_btn)

        layout.addLayout(btn_lay)

        self.answer_rows = []
        self.q_type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._load_answers()

    def _on_type_changed(self, index):
        is_written = (index == 2)
        is_matching = (index == 3)
        is_ordering = (index == 4)
        is_blanks = (index == 5)
        
        hints = {
            0: "💡 Одиночный выбор: укажите несколько вариантов ответов и отметьте галочкой один правильный.",
            1: "💡 Множественный выбор: укажите несколько вариантов ответов и отметьте галочками все правильные.",
            2: "💡 Письменный ответ: укажите возможные правильные формулировки ответа (галочки не нужны).",
            3: "💡 Соответствие: вводите пары в формате «Ключ = Значение» (например: HTTP = 80).",
            4: "💡 Порядок: добавьте элементы в правильной последовательности. При тестировании они будут перемешаны.",
            5: "💡 Пропуски: выделите пропуски скобками (например: Язык [Python]...). Для нескольких верных вариантов используйте |: [Python|Пайтон]. Если добавить варианты ниже, студент будет выбирать из них. Иначе — ввод вручную."
        }
        self.type_hint_lbl.setText(hints.get(index, ""))
        
        if is_written:
            self.ans_title_lbl.setText("Правильные варианты ответа (студент должен ввести любой из них):")
            self.add_ans_btn.setText("Добавить правильный вариант")
        elif is_matching:
            self.ans_title_lbl.setText("Пары соответствия в формате 'Ключ = Значение' (например: HTTP = 80):")
            self.add_ans_btn.setText("Добавить пару соответствия")
        elif is_ordering:
            self.ans_title_lbl.setText("Элементы в правильном порядке:")
            self.add_ans_btn.setText("Добавить элемент")
        elif is_blanks:
            self.ans_title_lbl.setText("Банк слов для выпадающих списков (необязательно):")
            self.add_ans_btn.setText("Добавить вариант в банк слов")
        else:
            self.ans_title_lbl.setText("Варианты ответов:")
            self.add_ans_btn.setText("Добавить вариант ответа")

        for row in self.answer_rows:
            if is_written or is_matching or is_ordering or is_blanks:
                row["cb"].setChecked(True)
                row["cb"].hide()
            else:
                row["cb"].show()

    def _load_answers(self):
        for ans in self.question.get("answers", []):
            self._create_answer_row(ans.get("text", ""), ans.get("correct", False))
        self._on_type_changed(self.q_type_combo.currentIndex())

    def _create_answer_row(self, text="", is_correct=False):
        row_widget = QWidget()
        row_widget.setStyleSheet(
            "QWidget { background-color: #ffffff; border: 1px solid #e7e5e4;"
            " border-radius: 8px; }"
        )
        row_lay = QHBoxLayout(row_widget)
        row_lay.setContentsMargins(8, 6, 8, 6)
        row_lay.setSpacing(8)

        # Checkbox for marking as correct
        correct_cb = QCheckBox()
        is_written = (self.q_type_combo.currentIndex() == 2)
        is_matching = (self.q_type_combo.currentIndex() == 3)
        is_ordering = (self.q_type_combo.currentIndex() == 4)
        is_blanks = (self.q_type_combo.currentIndex() == 5)
        if is_written or is_matching or is_ordering or is_blanks:
            correct_cb.setChecked(True)
            correct_cb.hide()
        else:
            correct_cb.setChecked(is_correct)

        correct_cb.setStyleSheet(
            "QCheckBox { background: transparent; border: none; }"
            "QCheckBox::indicator { width: 20px; height: 20px; }"
        )
        row_lay.addWidget(correct_cb)

        # Text input
        ans_input = QLineEdit()
        ans_input.setText(text)
        ans_input.setPlaceholderText("Текст ответа...")
        ans_input.setStyleSheet(
            "QLineEdit { background-color: #ffffff; border: 1px solid #d6d3d1;"
            " border-radius: 6px; padding: 6px 8px; font-size: 13px; color: #292524; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )
        row_lay.addWidget(ans_input, 1)

        # Delete button
        del_btn = QPushButton("Удалить")
        del_btn.setProperty("class", "tableDangerBtn")
        del_btn.setCursor(Qt.PointingHandCursor)

        def remove_row():
            row_widget.deleteLater()
            self.answer_rows.remove(row_info)

        del_btn.clicked.connect(remove_row)
        row_lay.addWidget(del_btn)

        row_info = {"widget": row_widget, "input": ans_input, "cb": correct_cb}
        self.answer_rows.append(row_info)

        self.scroll_content_layout.addWidget(row_widget)

    def _add_answer_row(self):
        self._create_answer_row()

    def _select_image(self):
        path, _ = QFileDialog.getOpenFileName(None, "Выберите изображение", "", "Изображения (*.png *.jpg *.jpeg *.gif)")
        if path:
            import base64
            try:
                with open(path, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                self.question["image_data"] = encoded
                self.img_status.setText("Изображение прикреплено")
                self.remove_img_btn.show()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить изображение: {e}")

    def _remove_image(self):
        self.question["image_data"] = None
        self.img_status.setText("Изображение отсутствует")
        self.remove_img_btn.hide()

    def _save_changes(self):
        text = self.q_text_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Предупреждение", "Текст вопроса не может быть пустым!")
            return

        answers_list = []
        q_type_idx = self.q_type_combo.currentIndex()
        is_written = (q_type_idx == 2)
        is_multiple = (q_type_idx == 1)
        is_matching = (q_type_idx == 3)
        is_ordering = (q_type_idx == 4)
        is_blanks = (q_type_idx == 5)

        for row in self.answer_rows:
            ans_text = row["input"].text().strip()
            if ans_text:
                if is_matching:
                    if '=' in ans_text:
                        parts = ans_text.split('=', 1)
                        key_part = parts[0].strip()
                        val_part = parts[1].strip()
                        answers_list.append({
                            "text": ans_text,
                            "key": key_part,
                            "value": val_part,
                            "correct": True
                        })
                    else:
                        answers_list.append({
                            "text": ans_text,
                            "key": ans_text,
                            "value": ans_text,
                            "correct": True
                        })
                else:
                    answers_list.append({
                        "text": ans_text,
                        "correct": True if (is_written or is_ordering or is_blanks) else row["cb"].isChecked()
                    })

        if not answers_list and not is_blanks:
            QMessageBox.warning(self, "Предупреждение", "Добавьте хотя бы один вариант ответа!")
            return
            
        if is_blanks:
            import re
            if not re.search(r'\[(.*?)\]', text):
                QMessageBox.warning(self, "Предупреждение", "Вопрос типа 'Пропуски' должен содержать хотя бы один пропуск в квадратных скобках (например: Язык [Python] является...).")
                return

        if not is_written and not is_matching and not is_ordering and not is_blanks:
            correct_count = sum(1 for a in answers_list if a["correct"])
            if correct_count == 0:
                QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы один правильный вариант ответа (отметьте галочкой)!")
                return

        self.question["text"] = text
        self.question["multiple"] = is_multiple
        self.question["written"] = is_written
        self.question["matching"] = is_matching
        self.question["ordering"] = is_ordering
        self.question["blanks"] = is_blanks
        self.question["answers"] = answers_list

        self.accept()


# ---------------------------------------------------------------------------
# Диалог мониторинга в реальном времени
# ---------------------------------------------------------------------------
class MonitoringDialog(QDialog):
    def __init__(self, exam_server, group=None, parent=None):
        super().__init__(parent)
        self.exam_server = exam_server
        self.group = group
        if group:
            self.setWindowTitle(f"Мониторинг группы {group}")
        else:
            self.setWindowTitle("Мониторинг тестирования в реальном времени")
        apply_dialog_scaling(self, parent, 820, 470)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = _title_label(
            f"Подключенные студенты ({group})" if group else "Подключенные студенты"
        )
        layout.addWidget(title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Имя студента", "Группа", "Статус", "Результат", "Процент"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 110)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        self.table.doubleClicked.connect(self.view_answers)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.view_answers_btn = QPushButton("Посмотреть ответы")
        self.view_answers_btn.setProperty("class", "primaryBtn")
        self.view_answers_btn.setCursor(Qt.PointingHandCursor)
        self.view_answers_btn.clicked.connect(self.view_answers)
        btn_layout.addWidget(self.view_answers_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setProperty("class", "secondaryBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

        # Таймер обновления данных
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_data)
        self.timer.start()

        self.update_data()

    def view_answers(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите студента из списка!")
            return

        students = list(self.exam_server._monitor_data.values())
        if self.group:
            students = [s for s in students if s.group.lower() == self.group.lower()]

        if row < len(students):
            student = students[row]

            # Находим правильные вопросы для этого студента
            questions = getattr(student, 'questions', None)
            if not questions:
                group_key = student.group.lower()
                questions = self.exam_server.questions
                if group_key in self.exam_server._active_exams:
                    questions = self.exam_server._active_exams[group_key]['questions']

            dlg = StudentAnswersDialog(student, questions, self)
            dlg.exec()

    def update_data(self):
        # Получаем данные мониторинга из истории активной сессии
        students = list(self.exam_server._monitor_data.values())
        if self.group:
            students = [s for s in students if s.group.lower() == self.group.lower()]

        # Динамически регулируем количество строк, предотвращая мерцание
        if self.table.rowCount() != len(students):
            self.table.setRowCount(len(students))

        for row, s in enumerate(students):
            # Проверяем или создаем ячейку для ФИО
            name_item = self.table.item(row, 0)
            if not name_item:
                name_item = QTableWidgetItem()
                self.table.setItem(row, 0, name_item)
            name_item.setText(s.name)

            # Проверяем или создаем ячейку для группы
            group_item = self.table.item(row, 1)
            if not group_item:
                group_item = QTableWidgetItem()
                self.table.setItem(row, 1, group_item)
            group_item.setText(s.group)

            # Проверяем или создаем ячейку для статуса
            status_item = self.table.item(row, 2)
            if not status_item:
                status_item = QTableWidgetItem()
                self.table.setItem(row, 2, status_item)

            if s.finished:
                warn_count = len(getattr(s, 'cheat_warnings', []))
                if warn_count >= 3:
                    status_item.setText("Сдан (Блокировка ⚠️)")
                    status_item.setForeground(QColor("#dc2626"))
                else:
                    status_item.setText("Сдал тест")
                    status_item.setForeground(QColor("#16a34a"))
            elif not s.active:
                status_item.setText("Соединение потеряно")
                status_item.setForeground(QColor("#dc2626"))
            else:
                warn_count = len(getattr(s, 'cheat_warnings', []))
                if warn_count > 0:
                    status_item.setText(f"Выполняет (⚠️ Предупр: {warn_count}/3)")
                    status_item.setForeground(QColor("#e11d48"))
                else:
                    status_item.setText("Выполняет тест")
                    status_item.setForeground(QColor("#2563eb"))

            # Проверяем или создаем ячейку для результата
            score_item = self.table.item(row, 3)
            if not score_item:
                score_item = QTableWidgetItem()
                self.table.setItem(row, 3, score_item)
            score_str = s.score if s.score else "В процессе"
            score_item.setText(score_str)

            # Проверяем или создаем ячейку для оценки
            grade_item = self.table.item(row, 4)
            if not grade_item:
                grade_item = QTableWidgetItem()
                self.table.setItem(row, 4, grade_item)
            if s.score:
                grade_text, grade_color = get_grade_details(s.score)
                grade_item.setText(grade_text)
                grade_item.setForeground(QColor(grade_color))
            else:
                grade_item.setText("—")
                grade_item.setForeground(QColor("#78716c"))


# ---------------------------------------------------------------------------
# Зона сброса файлов (Drag and Drop)
# ---------------------------------------------------------------------------
class DropZoneWidget(QFrame):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        self.label = QLabel("Перетащите файл теста формата .txt сюда")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size: 15px; color: #78716c; font-weight: bold; border: none;")
        layout.addWidget(self.label)

        btn_row = QHBoxLayout()
        btn_row.setAlignment(Qt.AlignCenter)

        browse_btn = QPushButton("Обзор файлов")
        browse_btn.setProperty("class", "secondaryBtn")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)
        btn_row.addWidget(browse_btn)

        layout.addLayout(btn_row)

        self._status_label = QLabel("Файл не выбран")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet("font-size: 13px; color: #a8a29e; border: none;")
        layout.addWidget(self._status_label)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(None, "Выберите файл теста", "", "Текстовые файлы (*.txt)")
        if path:
            self.set_file(path)

    def set_file(self, path):
        self._status_label.setText(f"Выбран файл: {os.path.basename(path)}")
        self._status_label.setStyleSheet("font-size: 13px; color: #16a34a; font-weight: bold; border: none;")
        self.file_dropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith('.txt'):
                self.set_file(path)
                break


class SelectTestFromRepoDialog(QDialog):
    def __init__(self, tests, parent=None):
        super().__init__(parent)
        self.tests = tests
        self.setWindowTitle("Выбрать тест из репозитория")
        apply_dialog_scaling(self, parent, 520, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = _section_label("Выберите тест из сохранённых")
        layout.addWidget(title)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию или группе…")
        self.search_input.setStyleSheet(
            "QLineEdit { padding: 9px 12px; font-size: 13px; border-radius: 8px;"
            " border: 1px solid #e7e5e4; background-color: #ffffff; color: #1c1917; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )
        self.search_input.textChanged.connect(self._filter_table)
        layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Название теста / Группа", "Вопросов"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 320)
        self.table.setColumnWidth(1, 120)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        layout.addWidget(self.table)

        self._filter_table()

        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setProperty("class", "secondaryBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(cancel_btn)

        self.select_btn = QPushButton("Выбрать")
        self.select_btn.setProperty("class", "primaryBtn")
        self.select_btn.setCursor(Qt.PointingHandCursor)
        self.select_btn.clicked.connect(self.accept)
        btn_lay.addWidget(self.select_btn)

        layout.addLayout(btn_lay)
        self.selected_group = None

        self.table.doubleClicked.connect(self.accept)

    def _filter_table(self):
        query = self.search_input.text().strip().lower()
        self.table.setRowCount(0)
        for t in self.tests:
            if not query or query in t["group"].lower():
                row = self.table.rowCount()
                self.table.insertRow(row)
                self.table.setItem(row, 0, QTableWidgetItem(t["group"]))
                self.table.setItem(row, 1, QTableWidgetItem(str(len(t["questions"]))))

    def accept(self):
        selected = self.table.currentRow()
        if selected >= 0:
            self.selected_group = self.table.item(selected, 0).text()
            super().accept()
        else:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тест!")


class UpdateProgressDialog(QDialog):
    def __init__(self, exam_server, parent=None):
        from PySide6.QtWidgets import (
            QFrame,
            QHBoxLayout,
            QLabel,
            QProgressBar,
            QPushButton,
            QScrollArea,
            QVBoxLayout,
            QWidget,
        )
        super().__init__(parent)
        self.exam_server = exam_server
        self.setWindowTitle("Обновление системы")
        apply_dialog_scaling(self, parent, 580, 470)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = _title_label("Установка системных обновлений")
        layout.addWidget(title_label)

        # Section 1: Server Device Progress
        server_frame = QFrame()
        server_frame.setObjectName("server_card")
        server_frame.setStyleSheet("""
            QFrame#server_card {
                background-color: #ffffff;
                border: 1px solid #e7e5e4;
                border-radius: 10px;
            }
        """)
        server_lay = QVBoxLayout(server_frame)
        server_lay.setContentsMargins(14, 14, 14, 14)
        server_lay.setSpacing(8)

        self.server_title = _section_label("Локальный сервер (загрузка с GitHub)")
        server_lay.addWidget(self.server_title)

        self.server_progress = QProgressBar()
        self.server_progress.setValue(0)
        server_lay.addWidget(self.server_progress)

        self.server_status = _muted_label("Ожидание…", size=11)
        server_lay.addWidget(self.server_status)

        layout.addWidget(server_frame)

        # Section 2: Connected Clients List
        clients_label = _section_label("Подключённые клиенты (передача обновлений)")
        layout.addWidget(clients_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #e7e5e4; border-radius: 8px; background-color: #ffffff; }")

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("scroll_content")
        self.scroll_content.setStyleSheet("#scroll_content { background-color: #ffffff; }")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(12)
        self.scroll_layout.setContentsMargins(12, 12, 12, 12)

        scroll.setWidget(self.scroll_content)
        layout.addWidget(scroll, 1)

        # Bottom Buttons
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setProperty("class", "secondaryBtn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(self.cancel_btn)

        self.upgrade_btn = QPushButton("Обновить все")
        self.upgrade_btn.setProperty("class", "primaryBtn")
        self.upgrade_btn.setCursor(Qt.PointingHandCursor)
        self.upgrade_btn.setEnabled(False)
        self.upgrade_btn.clicked.connect(self.apply_full_upgrade)
        btn_lay.addWidget(self.upgrade_btn)

        layout.addLayout(btn_lay)

        self.client_widgets = {} # sock -> (name_lbl, progress_bar, status_lbl)
        self._populate_clients()

        # Реалтайм-обновление списка клиентов в диалоге обновления
        self.exam_server.student_connected.connect(self._on_student_changed)
        self.exam_server.student_disconnected.connect(self._on_student_changed)

    def _on_student_changed(self, name, group):
        self._populate_clients()

    def reject(self):
        try:
            self.exam_server.student_connected.disconnect(self._on_student_changed)
            self.exam_server.student_disconnected.disconnect(self._on_student_changed)
        except Exception:
            pass
        super().reject()

    def closeEvent(self, event):
        try:
            self.exam_server.student_connected.disconnect(self._on_student_changed)
            self.exam_server.student_disconnected.disconnect(self._on_student_changed)
        except Exception:
            pass
        super().closeEvent(event)

    def _populate_clients(self):
        from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget
        # Очистить предыдущие виджеты
        for i in reversed(range(self.scroll_layout.count())):
            item = self.scroll_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                w.setParent(None)
                w.deleteLater()

        self.client_widgets.clear()

        students = list(self.exam_server._students.values())
        if not students:
            empty_lbl = _muted_label("Нет подключённых клиентов.", size=12)
            self.scroll_layout.addWidget(empty_lbl)
            return

        for s in students:
            item_widget = QWidget()
            item_lay = QVBoxLayout(item_widget)
            item_lay.setContentsMargins(0, 0, 0, 8)
            item_lay.setSpacing(4)

            info_lay = QHBoxLayout()
            name_lbl = QLabel(f"{s.name} ({s.group})")
            name_lbl.setStyleSheet(
                "font-size: 12px; font-weight: 600; color: #44403c;"
                " border: none; background: transparent;"
            )
            ver_lbl = QLabel(f"Версия: {s.version}")
            ver_lbl.setStyleSheet(
                "font-size: 11px; color: #78716c; border: none; background: transparent;"
            )
            info_lay.addWidget(name_lbl)
            info_lay.addStretch()
            info_lay.addWidget(ver_lbl)
            item_lay.addLayout(info_lay)

            prog = QProgressBar()
            prog.setValue(0)
            prog.setFixedHeight(10)
            prog.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #e7e5e4;
                    border-radius: 4px;
                    background-color: #f5f5f4;
                    text-align: center;
                    font-size: 9px;
                    color: transparent;
                }
                QProgressBar::chunk {
                    background-color: #2563eb;
                    border-radius: 3px;
                }
            """)
            item_lay.addWidget(prog)

            status_lbl = QLabel("Ожидание скачивания сервера…")
            status_lbl.setStyleSheet(
                "font-size: 10px; color: #a8a29e; border: none; background: transparent;"
            )
            item_lay.addWidget(status_lbl)

            # Разделительная полоса
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setFrameShadow(QFrame.Plain)
            sep.setStyleSheet("color: #f5f5f4;")
            item_lay.addWidget(sep)

            self.scroll_layout.addWidget(item_widget)
            self.client_widgets[s.socket] = (name_lbl, prog, status_lbl)

    def set_server_progress(self, percent, text):
        self.server_progress.setValue(percent)
        self.server_status.setText(text)

    def set_client_progress(self, socket, percent, text):
        if socket in self.client_widgets:
            _, prog, status_lbl = self.client_widgets[socket]
            prog.setValue(percent)
            status_lbl.setText(text)
            if percent == 100:
                status_lbl.setStyleSheet("font-size: 10px; color: #15803d; font-weight: bold;")
            else:
                status_lbl.setStyleSheet("font-size: 10px; color: #2563eb;")

    def enable_upgrade(self):
        self.upgrade_btn.setEnabled(True)

    def apply_full_upgrade(self):
        import os
        import platform
        import shutil
        import subprocess
        import sys

        from PySide6.QtWidgets import QApplication

        # Рассылка перезагрузки клиентам
        self.exam_server.send_reboot_to_all_clients()

        # Перезагрузка сервера
        current_exe = os.path.abspath(sys.argv[0])
        update_file = current_exe + ".new"

        # Если запущен скрипт .py, мы не заменяем его бинарным файлом.
        # Просто перезапускаем текущий .py с помощью sys.executable.
        if current_exe.endswith('.py'):
            if platform.system() == 'Windows':
                subprocess.Popen([sys.executable, current_exe])
            else:
                subprocess.Popen([sys.executable, current_exe])
            QApplication.quit()
            return

        # Для скомпилированного бинарника: ищем скачанный с GitHub файл сервера в updates/
        upd_dir = self.exam_server.get_updates_dir()
        if os.path.exists(upd_dir):
            server_os = platform.system().lower()
            for f in os.listdir(upd_dir):
                name_lower = f.lower()
                if 'server' in name_lower:
                    if server_os == 'windows' and not name_lower.endswith('.exe'):
                        continue
                    if server_os == 'linux' and name_lower.endswith('.exe'):
                        continue

                    src_path = os.path.join(upd_dir, f)
                    try:
                        shutil.copy2(src_path, update_file)
                        break
                    except Exception as e:
                        print(f"Ошибка при копировании файла обновления сервера: {e}")

        if os.path.exists(update_file):
            if platform.system() == 'Windows':
                updater_script = "update.bat"
                with open(updater_script, 'w') as f:
                    f.write('@echo off\n')
                    f.write('timeout /t 2 /nobreak > nul\n')
                    f.write(f'del "{current_exe}"\n')
                    f.write(f'move "{update_file}" "{current_exe}"\n')
                    f.write(f'start "" "{current_exe}"\n')
                    f.write('del "%~f0"\n')
                subprocess.Popen([updater_script], shell=True)
            else:
                updater_script = "update.sh"
                with open(updater_script, 'w') as f:
                    f.write('#!/bin/bash\n')
                    f.write('sleep 2\n')
                    f.write(f'mv "{update_file}" "{current_exe}"\n')
                    f.write(f'chmod +x "{current_exe}"\n')
                    f.write(f'"{current_exe}" &\n')
                    f.write('rm "$0"\n')
                os.chmod(updater_script, 0o755)
                subprocess.Popen(["/bin/bash", updater_script])

        QApplication.quit()


class ConnectedClientsDialog(QDialog):
    def __init__(self, exam_server, parent=None):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QHBoxLayout,
            QHeaderView,
            QLabel,
            QPushButton,
            QTableWidget,
            QVBoxLayout,
        )
        super().__init__(parent)
        self.exam_server = exam_server
        self.setWindowTitle("Подключённые клиенты")
        apply_dialog_scaling(self, parent, 880, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Title
        title_label = _title_label("Список подключённых клиентов")
        layout.addWidget(title_label)

        # Description hint
        desc_label = _muted_label(
            "Здесь отображаются устройства студентов, которые сейчас подключены к серверу и проходят тестирование."
        )
        layout.addWidget(desc_label)

        # Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Имя студента", "Группа", "ОС", "Версия клиента", "IP-адрес / Порт"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 260)
        self.table.setColumnWidth(1, 110)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 160)
        self.table.setColumnWidth(4, 180)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(True)
        layout.addWidget(self.table)

        # Actions layout
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setProperty("class", "secondaryBtn")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        btn_lay.addWidget(close_btn)

        layout.addLayout(btn_lay)

        # Timer for real-time updates
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_clients)
        self.timer.start()

        self.update_clients()

    def update_clients(self):
        from PySide6.QtWidgets import QTableWidgetItem
        students = list(self.exam_server._students.values())

        if self.table.rowCount() != len(students):
            self.table.setRowCount(len(students))

        for row, s in enumerate(students):
            # Name
            name_item = self.table.item(row, 0)
            if not name_item:
                name_item = QTableWidgetItem()
                self.table.setItem(row, 0, name_item)
            name_item.setText(s.name)

            # Group
            group_item = self.table.item(row, 1)
            if not group_item:
                group_item = QTableWidgetItem()
                self.table.setItem(row, 1, group_item)
            group_item.setText(s.group)

            # OS
            os_item = self.table.item(row, 2)
            if not os_item:
                os_item = QTableWidgetItem()
                self.table.setItem(row, 2, os_item)
            os_item.setText(str(s.os).capitalize())

            # Version
            ver_item = self.table.item(row, 3)
            if not ver_item:
                ver_item = QTableWidgetItem()
                self.table.setItem(row, 3, ver_item)
            ver_item.setText(s.version)

            # IP / Port
            peer_item = self.table.item(row, 4)
            if not peer_item:
                peer_item = QTableWidgetItem()
                self.table.setItem(row, 4, peer_item)
            try:
                peer_ip = s.socket.peerAddress().toString().removeprefix("::ffff:")
                peer_port = s.socket.peerPort()
                peer_item.setText(f"{peer_ip}:{peer_port}")
            except Exception:
                peer_item.setText("Неизвестно")


