import os

from PySide6.QtCore import QDir, QModelIndex, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileSystemModel,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeView,
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
                    sel_lbl = QLabel("Сопоставлено:\n" + "\n".join(f"• {pa}" for pa in student_ans) if student_ans else "Сопоставлено: [нет ответа]")
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
                    cor_lbl = QLabel("Правильные пары соответствия:\n" + "\n".join(correct_pairs_list))
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
        path, _ = StyledFileDialog.get_open_file_name(
            self,
            "Выберите изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.gif *.bmp);;Все файлы (*.*)",
        )
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
        path, _ = StyledFileDialog.get_open_file_name(
            self,
            "Выберите файл теста",
            "",
            "Текстовые файлы (*.txt);;JSON файлы (*.json);;Все файлы (*.*)",
        )
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
        apply_dialog_scaling(self, parent, 580, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = _section_label("Выберите тест из сохранённых")
        layout.addWidget(title)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию или каталогу…")
        self.search_input.setStyleSheet(
            "QLineEdit { padding: 9px 12px; font-size: 13px; border-radius: 8px;"
            " border: 1px solid #e7e5e4; background-color: #ffffff; color: #1c1917; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )
        self.search_input.textChanged.connect(self._filter_table)
        layout.addWidget(self.search_input)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Каталог", "Название теста", "Вопросов"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 160)
        self.table.setColumnWidth(1, 260)
        self.table.setColumnWidth(2, 100)
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
            group_full = t.get("group", "")
            if " / " in group_full:
                parts = group_full.split(" / ")
                folder = " / ".join(parts[:-1])
                test_name = parts[-1]
            else:
                folder = "—"
                test_name = group_full

            display_name = t.get("title") or test_name

            if not query or query in group_full.lower() or query in display_name.lower():
                row = self.table.rowCount()
                self.table.insertRow(row)

                folder_item = QTableWidgetItem(folder)
                test_item = QTableWidgetItem(display_name)
                test_item.setData(Qt.UserRole, group_full)
                q_count_item = QTableWidgetItem(str(len(t.get("questions", []))))

                self.table.setItem(row, 0, folder_item)
                self.table.setItem(row, 1, test_item)
                self.table.setItem(row, 2, q_count_item)

    def accept(self):
        selected = self.table.currentRow()
        if selected >= 0:
            item = self.table.item(selected, 1)
            if item:
                self.selected_group = item.data(Qt.UserRole) or item.text()
            else:
                self.selected_group = self.table.item(selected, 0).text()
            super().accept()
        else:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тест!")


class UpdateProgressDialog(QDialog):
    def __init__(self, exam_server, parent=None, target_version=None):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (
            QFrame,
            QHBoxLayout,
            QProgressBar,
            QPushButton,
            QScrollArea,
            QVBoxLayout,
            QWidget,
        )
        super().__init__(parent)
        self.exam_server = exam_server
        self.target_version = target_version
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
        import shutil
        import subprocess
        import sys

        from PySide6.QtWidgets import QApplication, QMessageBox

        from shared.system import (
            get_current_executable_path,
            get_server_update_file,
            run_updater_script,
        )

        # Рассылка перезагрузки клиентам
        self.exam_server.send_reboot_to_all_clients()

        # Перезагрузка сервера
        current_exe = get_current_executable_path()
        update_file = current_exe + ".new"

        # Если запущен скрипт .py, мы не заменяем его бинарным файлом.
        # Просто перезапускаем текущий .py с помощью sys.executable.
        if current_exe.endswith(".py"):
            subprocess.Popen([sys.executable, current_exe])
            QApplication.quit()
            return

        # Для скомпилированного бинарника: ищем скачанный с GitHub файл сервера в updates/
        upd_dir = self.exam_server.get_updates_dir()
        target_version = getattr(self, "target_version", None)
        server_binary = get_server_update_file(upd_dir, version_tag=target_version)
        if server_binary and os.path.exists(server_binary):
            try:
                shutil.copy2(server_binary, update_file)
                self.exam_server.log_message.emit(
                    f"Подготовлен файл обновления сервера: {server_binary} -> {update_file}"
                )
            except Exception as e:
                self.exam_server.log_message.emit(
                    f"Ошибка при копировании файла обновления сервера: {e}"
                )
                QMessageBox.critical(
                    self,
                    "Ошибка обновления",
                    f"Не удалось подготовить файл обновления:\n{e}",
                )
                return
        else:
            self.exam_server.log_message.emit(
                f"Файл обновления сервера не найден в {upd_dir} (целевая версия: {target_version})"
            )
            QMessageBox.warning(
                self,
                "Файл не найден",
                f"Файл обновления сервера не найден в папке {upd_dir}.",
            )
            return

        if os.path.exists(update_file):
            success = run_updater_script(current_exe, update_file)
            if success:
                QApplication.quit()
            else:
                QMessageBox.critical(
                    self,
                    "Ошибка обновления",
                    "Не удалось запустить скрипт обновления.",
                )
        else:
            QMessageBox.warning(
                self,
                "Файл не найден",
                "Файл обновления сервера не найден.",
            )


class ConnectedClientsDialog(QDialog):
    def __init__(self, exam_server, parent=None):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import (
            QAbstractItemView,
            QHBoxLayout,
            QHeaderView,
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


class StyledFileDialog(QDialog):
    """
    Единый двухпанельный файловый менеджер и диалог выбора файлов/папок
    в фирменном дизайне TTGTiSO-Test.
    Поддерживает режимы:
      - OPEN_FILE: выбор существующего файла
      - SAVE_FILE: сохранение/создание файла с автодополнением расширения
      - CHOOSE_DIR: выбор папки
    """
    class Mode:
        OPEN_FILE = "open_file"
        SAVE_FILE = "save_file"
        CHOOSE_DIR = "choose_dir"

    def __init__(
        self,
        parent=None,
        title: str = "",
        initial_path: str = "",
        filter_str: str = "",
        mode: str = Mode.OPEN_FILE,
        default_filename: str = "",
    ):
        super().__init__(parent)
        self.mode = mode
        self.filter_str = filter_str
        self.selected_file = ""
        self.selected_path = ""
        self.selected_filter = ""
        self.parsed_filters = []

        # Установка заголовка окна
        if title:
            self.setWindowTitle(title)
        elif mode == self.Mode.SAVE_FILE:
            self.setWindowTitle("Сохранить файл")
        elif mode == self.Mode.CHOOSE_DIR:
            self.setWindowTitle("Выбор папки")
        else:
            self.setWindowTitle("Открыть файл")

        self.resize(840, 540)
        self.setMinimumSize(700, 440)
        self.setStyleSheet(GLOBAL_QSS)

        # Определение начальной директории и имени файла
        init_file = default_filename or ""
        if initial_path:
            if os.path.isfile(initial_path):
                init_dir = os.path.dirname(initial_path)
                if not init_file:
                    init_file = os.path.basename(initial_path)
            elif os.path.isdir(initial_path):
                init_dir = initial_path
            else:
                parent_dir = os.path.dirname(initial_path)
                if os.path.isdir(parent_dir):
                    init_dir = parent_dir
                    if not init_file:
                        init_file = os.path.basename(initial_path)
                else:
                    init_dir = os.path.expanduser("~")
                    if not init_file:
                        init_file = os.path.basename(initial_path)
        else:
            # По умолчанию открываем Загрузки или Репозиторий тестов или Домашнюю папку
            downloads = os.path.expanduser("~/Downloads")
            if os.path.exists(downloads):
                init_dir = downloads
            else:
                init_dir = os.path.expanduser("~")

        self.current_dir = os.path.abspath(init_dir if os.path.exists(init_dir) else os.path.expanduser("~"))
        self.selected_path = self.current_dir

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Заголовок диалога
        header_title = title or self.windowTitle()
        title_lbl = QLabel(header_title)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #1c1917;")
        layout.addWidget(title_lbl)

        # Верхняя панель навигации (Папка, Путь, Кнопка Вверх)
        nav_box = QHBoxLayout()
        nav_box.setSpacing(8)

        lbl_cur = QLabel("Папка:")
        lbl_cur.setStyleSheet("font-weight: 600; color: #57534e;")
        nav_box.addWidget(lbl_cur)

        self.path_edit = QLineEdit(self.current_dir)
        self.path_edit.setStyleSheet(
            "QLineEdit { padding: 7px 12px; font-size: 13px;"
            " background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 8px; }"
        )
        self.path_edit.returnPressed.connect(self._on_path_entered)
        nav_box.addWidget(self.path_edit, 1)

        up_btn = QPushButton("Вверх ⬆")
        up_btn.setProperty("class", "secondaryBtn")
        up_btn.setCursor(Qt.PointingHandCursor)
        up_btn.clicked.connect(self._go_up)
        nav_box.addWidget(up_btn)

        layout.addLayout(nav_box)

        # Сплиттер (Левая панель — Быстрый доступ, Правая — Проводник файлов/папок)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #e7e5e4; width: 1px; }")

        # 1. Быстрый доступ
        left_container = QWidget()
        left_lay = QVBoxLayout(left_container)
        left_lay.setContentsMargins(0, 0, 8, 0)
        left_lay.setSpacing(6)

        lbl_places = QLabel("Быстрый доступ")
        lbl_places.setStyleSheet("font-size: 11px; font-weight: 700; color: #78716c; text-transform: uppercase;")
        left_lay.addWidget(lbl_places)

        self.places_list = QListWidget()
        self.places_list.setStyleSheet(
            "QListWidget {"
            "  background-color: #f5f5f4;"
            "  border: 1px solid #e7e5e4;"
            "  border-radius: 8px;"
            "  padding: 4px;"
            "  outline: 0;"
            "}"
            "QListWidget::item {"
            "  padding: 8px 10px;"
            "  border-radius: 6px;"
            "  color: #1c1917;"
            "  font-weight: 500;"
            "  font-size: 12.5px;"
            "}"
            "QListWidget::item:hover {"
            "  background-color: #e7e5e4;"
            "}"
            "QListWidget::item:selected {"
            "  background-color: #e0f2fe;"
            "  color: #0369a1;"
            "  font-weight: 600;"
            "}"
        )

        try:
            from .storage import default_tests_dir, tests_dir
        except ImportError:
            from storage import default_tests_dir, tests_dir

        active_repo = str(tests_dir()) if os.path.exists(str(tests_dir())) else str(default_tests_dir())
        self.places = [
            ("📁 Репозиторий тестов", active_repo),
            ("🏠 Домашняя папка", os.path.expanduser("~")),
            ("🖥️ Рабочий стол", os.path.expanduser("~/Desktop")),
            ("📄 Документы", os.path.expanduser("~/Documents")),
            ("📥 Загрузки", os.path.expanduser("~/Downloads")),
            ("💾 Диск / Корень (/)", "/"),
        ]

        if os.name == 'nt':
            import string
            for letter in string.ascii_uppercase:
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    self.places.append((f"💾 Диск ({letter}:)", drive))

        for label, p in self.places:
            if os.path.exists(p):
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, p)
                self.places_list.addItem(item)

        self.places_list.itemClicked.connect(self._on_place_clicked)
        left_lay.addWidget(self.places_list)
        splitter.addWidget(left_container)

        # 2. Правая панель: Файловая структура
        right_container = QWidget()
        right_lay = QVBoxLayout(right_container)
        right_lay.setContentsMargins(8, 0, 0, 0)
        right_lay.setSpacing(6)

        lbl_tree = QLabel("Файлы и папки" if self.mode != self.Mode.CHOOSE_DIR else "Дерево каталогов")
        lbl_tree.setStyleSheet("font-size: 11px; font-weight: 700; color: #78716c; text-transform: uppercase;")
        right_lay.addWidget(lbl_tree)

        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        self.model.setNameFilterDisables(False)

        if self.mode == self.Mode.CHOOSE_DIR:
            self.model.setFilter(QDir.Dirs | QDir.NoDotAndDotDot | QDir.Drives)
        else:
            self.model.setFilter(QDir.AllEntries | QDir.NoDotAndDotDot | QDir.Drives)

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setAnimated(True)
        self.tree.setSortingEnabled(True)
        self.tree.sortByColumn(0, Qt.AscendingOrder)
        self.tree.setStyleSheet(
            "QTreeView {"
            "  background-color: #ffffff;"
            "  border: 1px solid #e7e5e4;"
            "  border-radius: 8px;"
            "  padding: 4px;"
            "  font-size: 13px;"
            "  outline: 0;"
            "}"
            "QTreeView::item {"
            "  padding: 5px 6px;"
            "  border-radius: 4px;"
            "}"
            "QTreeView::item:hover {"
            "  background-color: #f5f5f4;"
            "}"
            "QTreeView::item:selected {"
            "  background-color: #e0f2fe;"
            "  color: #0369a1;"
            "  font-weight: 600;"
            "}"
            "QHeaderView::section {"
            "  background-color: #f5f5f4;"
            "  color: #57534e;"
            "  font-weight: 600;"
            "  font-size: 11px;"
            "  padding: 5px 8px;"
            "  border: none;"
            "  border-bottom: 1px solid #e7e5e4;"
            "}"
        )

        if self.mode == self.Mode.CHOOSE_DIR:
            self.tree.setHeaderHidden(True)
            self.tree.setColumnHidden(1, True)
            self.tree.setColumnHidden(2, True)
            self.tree.setColumnHidden(3, True)
        else:
            self.tree.setHeaderHidden(False)
            self.tree.header().setStretchLastSection(True)
            self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
            self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.tree.clicked.connect(self._on_tree_clicked)
        self.tree.doubleClicked.connect(self._on_tree_double_clicked)
        right_lay.addWidget(self.tree)
        splitter.addWidget(right_container)

        splitter.setSizes([220, 600])
        layout.addWidget(splitter, 1)

        # Нижняя панель с фильтрами и именем файла (для файловых режимов)
        if self.mode != self.Mode.CHOOSE_DIR:
            file_info_layout = QVBoxLayout()
            file_info_layout.setSpacing(8)

            # Строка "Имя файла"
            fn_row = QHBoxLayout()
            fn_row.setSpacing(8)
            lbl_fn = QLabel("Имя файла:")
            lbl_fn.setMinimumWidth(80)
            lbl_fn.setStyleSheet("font-weight: 600; color: #57534e;")
            fn_row.addWidget(lbl_fn)

            self.file_name_edit = QLineEdit(init_file)
            self.file_name_edit.setStyleSheet(
                "QLineEdit { padding: 7px 12px; font-size: 13px;"
                " background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 8px; }"
            )
            self.file_name_edit.returnPressed.connect(self._accept_selection)
            fn_row.addWidget(self.file_name_edit, 1)
            file_info_layout.addLayout(fn_row)

            # Строка "Тип файлов" (фильтр)
            ft_row = QHBoxLayout()
            ft_row.setSpacing(8)
            lbl_ft = QLabel("Тип файлов:")
            lbl_ft.setMinimumWidth(80)
            lbl_ft.setStyleSheet("font-weight: 600; color: #57534e;")
            ft_row.addWidget(lbl_ft)

            self.filter_combo = StyledComboBox()
            self.filter_combo.setStyleSheet(
                "QComboBox { padding: 6px 12px; font-size: 13px;"
                " background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 8px; }"
            )
            self._setup_filters(filter_str)
            self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
            ft_row.addWidget(self.filter_combo, 1)
            file_info_layout.addLayout(ft_row)

            layout.addLayout(file_info_layout)

        # Нижняя панель действий (Создать папку, Отмена, Выбрать/Открыть/Сохранить)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        new_folder_btn = QPushButton("+ Создать папку")
        new_folder_btn.setProperty("class", "secondaryBtn")
        new_folder_btn.setCursor(Qt.PointingHandCursor)
        new_folder_btn.clicked.connect(self._create_folder)
        btn_layout.addWidget(new_folder_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setProperty("class", "secondaryBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        if self.mode == self.Mode.SAVE_FILE:
            action_text = "Сохранить"
        elif self.mode == self.Mode.CHOOSE_DIR:
            action_text = "Выбрать эту папку"
        else:
            action_text = "Открыть"

        self.action_btn = QPushButton(action_text)
        self.action_btn.setProperty("class", "primaryBtn")
        self.action_btn.setCursor(Qt.PointingHandCursor)
        self.action_btn.clicked.connect(self._accept_selection)
        btn_layout.addWidget(self.action_btn)

        layout.addLayout(btn_layout)

        # Применяем фильтр и раскрываем начальный каталог
        self._apply_active_filter()
        QTimer.singleShot(100, lambda: self._select_and_expand_path(self.current_dir))

    def _setup_filters(self, filter_str: str):
        self.parsed_filters = []
        if not filter_str:
            filter_str = "Все файлы (*.*)"

        import re
        parts = [p.strip() for p in filter_str.split(";;") if p.strip()]
        for part in parts:
            m = re.search(r'\((.*?)\)', part)
            if m:
                exts = m.group(1).split()
            else:
                exts = ["*.*"]
            self.parsed_filters.append((part, exts))
            self.filter_combo.addItem(part, exts)

    def _on_filter_changed(self, index: int):
        self._apply_active_filter()

    def _apply_active_filter(self):
        if self.mode == self.Mode.CHOOSE_DIR or not hasattr(self, 'filter_combo'):
            return
        idx = self.filter_combo.currentIndex()
        if idx >= 0:
            patterns = self.filter_combo.itemData(idx)
            if patterns:
                self.model.setNameFilters(patterns)
                self.selected_filter = self.filter_combo.currentText()

    def _select_and_expand_path(self, target_path: str):
        if not target_path or not os.path.exists(target_path):
            return
        abs_path = os.path.abspath(target_path)
        if os.path.isdir(abs_path):
            self.current_dir = abs_path
            self.selected_path = abs_path
        else:
            self.current_dir = os.path.dirname(abs_path)
            self.selected_path = abs_path
            if hasattr(self, 'file_name_edit'):
                self.file_name_edit.setText(os.path.basename(abs_path))

        self.path_edit.setText(self.current_dir)

        if self.mode == self.Mode.CHOOSE_DIR:
            idx = self.model.index(self.current_dir)
            if idx.isValid():
                parent = idx.parent()
                while parent.isValid():
                    self.tree.expand(parent)
                    parent = parent.parent()
                self.tree.expand(idx)
                self.tree.setCurrentIndex(idx)
                self.tree.scrollTo(idx, QAbstractItemView.PositionAtCenter)
        else:
            # В файловом режиме устанавливаем корень модели и дерева на текущую папку
            dir_idx = self.model.setRootPath(self.current_dir)
            self.tree.setRootIndex(dir_idx)

    def _on_path_entered(self):
        entered = self.path_edit.text().strip()
        if entered and os.path.exists(entered):
            self._select_and_expand_path(entered)
        else:
            QMessageBox.warning(self, "Предупреждение", f"Указанный путь не существует:\n{entered}")
            self.path_edit.setText(self.current_dir)

    def _on_place_clicked(self, item: QListWidgetItem):
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            self._select_and_expand_path(path)

    def _on_tree_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)
        if not path:
            return
        if os.path.isdir(path):
            self.selected_path = os.path.abspath(path)
            if self.mode == self.Mode.CHOOSE_DIR:
                self.path_edit.setText(self.selected_path)
        elif os.path.isfile(path):
            self.selected_file = os.path.abspath(path)
            if hasattr(self, 'file_name_edit'):
                self.file_name_edit.setText(os.path.basename(path))

    def _on_tree_double_clicked(self, index: QModelIndex):
        path = self.model.filePath(index)
        if not path:
            return
        if os.path.isdir(path):
            self._select_and_expand_path(path)
        elif os.path.isfile(path):
            self.selected_file = os.path.abspath(path)
            if hasattr(self, 'file_name_edit'):
                self.file_name_edit.setText(os.path.basename(path))
            self._accept_selection()

    def _go_up(self):
        parent_dir = os.path.dirname(self.current_dir)
        if parent_dir and os.path.isdir(parent_dir) and parent_dir != self.current_dir:
            self._select_and_expand_path(parent_dir)

    def _create_folder(self):
        folder_name, ok = QInputDialog.getText(self, "Новая папка", "Введите название новой папки:")
        if ok and folder_name.strip():
            new_path = os.path.join(self.current_dir, folder_name.strip())
            try:
                os.makedirs(new_path, exist_ok=True)
                self._select_and_expand_path(new_path)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось создать папку: {e}")

    def _accept_selection(self):
        if self.mode == self.Mode.CHOOSE_DIR:
            if self.selected_path and os.path.isdir(self.selected_path):
                self.accept()
            else:
                QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите существующую папку.")
            return

        file_name = self.file_name_edit.text().strip()
        if not file_name:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, укажите имя файла.")
            return

        if os.path.isabs(file_name):
            full_path = file_name
        else:
            full_path = os.path.join(self.current_dir, file_name)

        if self.mode == self.Mode.OPEN_FILE:
            if os.path.isdir(full_path):
                self._select_and_expand_path(full_path)
                return
            if not os.path.exists(full_path):
                QMessageBox.warning(self, "Предупреждение", f"Файл не найден:\n{full_path}")
                return
            self.selected_file = full_path
            self.accept()

        elif self.mode == self.Mode.SAVE_FILE:
            if os.path.isdir(full_path):
                self._select_and_expand_path(full_path)
                return

            # Автодополнение расширения при необходимости
            if "." not in os.path.basename(full_path):
                patterns = self.filter_combo.currentData() if hasattr(self, 'filter_combo') else []
                if patterns:
                    first_pat = patterns[0]
                    if first_pat.startswith("*.") and first_pat != "*.*":
                        full_path += first_pat[1:]

            self.selected_file = full_path
            self.accept()

    @classmethod
    def get_open_file_name(cls, parent=None, title="Открыть файл", directory="", filter_str="") -> tuple:
        dlg = cls(parent=parent, title=title, initial_path=directory, filter_str=filter_str, mode=cls.Mode.OPEN_FILE)
        if dlg.exec():
            return dlg.selected_file, dlg.selected_filter
        return "", ""

    @classmethod
    def get_save_file_name(cls, parent=None, title="Сохранить файл", directory="", filter_str="", default_filename="") -> tuple:
        dlg = cls(
            parent=parent,
            title=title,
            initial_path=directory,
            filter_str=filter_str,
            mode=cls.Mode.SAVE_FILE,
            default_filename=default_filename,
        )
        if dlg.exec():
            return dlg.selected_file, dlg.selected_filter
        return "", ""

    @classmethod
    def get_existing_directory(cls, parent=None, title="Выбор папки", directory="") -> str:
        dlg = cls(parent=parent, title=title, initial_path=directory, mode=cls.Mode.CHOOSE_DIR)
        if dlg.exec():
            return dlg.selected_path
        return ""


class DirectoryChooserDialog(StyledFileDialog):
    """Совместимый двухпанельный диалог выбора папки."""
    def __init__(self, initial_path: str = "", parent=None):
        super().__init__(
            parent=parent,
            title="Выбор папки для хранения тестов",
            initial_path=initial_path,
            mode=StyledFileDialog.Mode.CHOOSE_DIR,
        )


