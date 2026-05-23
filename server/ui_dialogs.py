import os
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox,
    QFrame, QTextEdit, QDialog, QAbstractItemView,
    QScrollArea, QCheckBox, QComboBox
)

try:
    from .styles import GLOBAL_QSS, get_scaled_qss
except ImportError:
    from styles import GLOBAL_QSS, get_scaled_qss

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
    dialog.setStyleSheet(get_scaled_qss(GLOBAL_QSS, scale_factor))

class StudentAnswersDialog(QDialog):
    def __init__(self, student, questions, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ответы студента: {student.name}")
        apply_dialog_scaling(self, parent, 700, 500)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Ответы студента: {student.name} ({student.group})")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; border: none;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #ffffff;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(16)
        scroll_layout.setContentsMargins(16, 16, 16, 16)
        scroll_layout.setAlignment(Qt.AlignTop)

        if not student.answers:
            no_ans = QLabel("Студент еще не отправил ответы.")
            no_ans.setStyleSheet("color: #64748b; font-size: 14px; font-weight: bold; border: none;")
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
                else:
                    is_correct = set(student_ans) == set(correct_answers)

                # Card for each question
                q_card = QFrame()
                q_card.setStyleSheet("background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
                card_lay = QVBoxLayout(q_card)
                card_lay.setSpacing(6)

                # Header with correctness badge
                header = QHBoxLayout()
                q_lbl = QLabel(f"Вопрос {q_num}: {q.get('text', '')}")
                q_lbl.setWordWrap(True)
                q_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #1e293b; border: none;")
                header.addWidget(q_lbl, 1)

                badge = QLabel()
                if is_correct:
                    badge.setText("Верно")
                    badge.setStyleSheet("background-color: #d1fae5; color: #065f46; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px; border: none;")
                else:
                    badge.setText("Неверно")
                    badge.setStyleSheet("background-color: #fee2e2; color: #991b1b; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 4px; border: none;")
                header.addWidget(badge)
                card_lay.addLayout(header)

                # Student selected
                if q.get('written'):
                    sel_lbl = QLabel(f"Ответ студента: {student_ans[0] if student_ans else '[Нет ответа]'}")
                else:
                    sel_lbl = QLabel(f"Выбрано студентом: {', '.join(student_ans) if student_ans else '[Нет ответа]'}")
                sel_lbl.setWordWrap(True)
                sel_lbl.setStyleSheet("font-size: 12px; color: #475569; border: none;")
                card_lay.addWidget(sel_lbl)

                # Correct answers
                if q.get('written'):
                    cor_lbl = QLabel(f"Правильные варианты ответа: {', '.join(correct_answers)}")
                else:
                    cor_lbl = QLabel(f"Правильный ответ: {', '.join(correct_answers)}")
                cor_lbl.setWordWrap(True)
                cor_lbl.setStyleSheet("font-size: 12px; color: #059669; font-weight: 500; border: none;")
                card_lay.addWidget(cor_lbl)

                scroll_layout.addWidget(q_card)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        close_btn = QPushButton("Закрыть")
        close_btn.setStyleSheet(
            "QPushButton { background-color: #6366f1; color: #ffffff; font-weight: bold; font-size: 13px; padding: 8px 16px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #4f46e5; }"
        )
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

        # Question Text
        lbl1 = QLabel("Текст вопроса:")
        lbl1.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(lbl1)

        self.q_text_input = QTextEdit()
        self.q_text_input.setPlaceholderText("Введите текст вопроса...")
        self.q_text_input.setPlainText(self.question.get("text", ""))
        self.q_text_input.setMaximumHeight(80)
        self.q_text_input.setStyleSheet(
            "QTextEdit { background-color: #ffffff; border: 2px solid #e2e8f0; border-radius: 8px; padding: 8px; font-size: 13px; color: #1e293b; }"
            "QTextEdit:focus { border: 2px solid #3b82f6; }"
        )
        layout.addWidget(self.q_text_input)

        # Question Type
        type_lay = QHBoxLayout()
        type_lbl = QLabel("Тип вопроса:")
        type_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        type_lay.addWidget(type_lbl)

        self.q_type_combo = QComboBox()
        self.q_type_combo.addItems([
            "Одиночный выбор",
            "Множественный выбор",
            "Письменный ответ"
        ])
        
        # Determine initial selection
        if self.question.get("written", False):
            self.q_type_combo.setCurrentIndex(2)
        elif self.question.get("multiple", False):
            self.q_type_combo.setCurrentIndex(1)
        else:
            self.q_type_combo.setCurrentIndex(0)
            
        type_lay.addWidget(self.q_type_combo)
        type_lay.addStretch()
        layout.addLayout(type_lay)

        # Image selection
        img_layout = QHBoxLayout()
        self.img_status = QLabel("Изображение отсутствует" if not self.question.get("image_data") else "Изображение прикреплено")
        self.img_status.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 500; border: none; background: transparent;")
        img_layout.addWidget(self.img_status)
        
        self.add_img_btn = QPushButton("Выбрать изображение")
        self.add_img_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; color: #1e293b; padding: 6px 12px; border-radius: 6px; border: 1px solid #cbd5e1; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background-color: #f1f5f9; }"
        )
        self.add_img_btn.clicked.connect(self._select_image)
        img_layout.addWidget(self.add_img_btn)
        
        self.remove_img_btn = QPushButton("Удалить")
        self.remove_img_btn.setStyleSheet(
            "QPushButton { background-color: #fee2e2; color: #991b1b; padding: 6px 12px; border-radius: 6px; border: none; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background-color: #fca5a5; }"
        )
        self.remove_img_btn.clicked.connect(self._remove_image)
        if not self.question.get("image_data"):
            self.remove_img_btn.hide()
        img_layout.addWidget(self.remove_img_btn)
        
        layout.addLayout(img_layout)

        # Answer Options List
        self.ans_title_lbl = QLabel("Варианты ответов:")
        self.ans_title_lbl.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(self.ans_title_lbl)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(
            "QScrollArea { border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff; }"
            "QScrollArea > QWidget > QWidget { background-color: #ffffff; }"
        )
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #ffffff;")
        self.scroll_content_layout = QVBoxLayout(self.scroll_content)
        self.scroll_content_layout.setSpacing(8)
        self.scroll_content_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_content_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        # Add Answer variant button
        self.add_ans_btn = QPushButton("Добавить вариант ответа")
        self.add_ans_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; color: #475569; font-weight: bold; font-size: 13px; padding: 10px; border-radius: 6px; border: 1px solid #cbd5e1; }"
            "QPushButton:hover { background-color: #f1f5f9; }"
        )
        self.add_ans_btn.clicked.connect(self._add_answer_row)
        layout.addWidget(self.add_ans_btn)

        # Bottom Buttons
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; color: #3b82f6; font-size: 13px; font-weight: bold; padding: 10px 20px; border: 2px solid #3b82f6; border-radius: 8px; }"
            "QPushButton:hover { background-color: #eff6ff; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(cancel_btn)

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 20px; border: none; border-radius: 8px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.save_btn.clicked.connect(self._save_changes)
        btn_lay.addWidget(self.save_btn)

        layout.addLayout(btn_lay)

        self.answer_rows = []
        self.q_type_combo.currentIndexChanged.connect(self._on_type_changed)
        self._load_answers()

    def _on_type_changed(self, index):
        is_written = (index == 2)
        if is_written:
            self.ans_title_lbl.setText("Правильные варианты ответа (студент должен ввести любой из них):")
            self.add_ans_btn.setText("Добавить правильный вариант")
        else:
            self.ans_title_lbl.setText("Варианты ответов:")
            self.add_ans_btn.setText("Добавить вариант ответа")

        for row in self.answer_rows:
            if is_written:
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
        row_widget.setStyleSheet("QWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; }")
        row_lay = QHBoxLayout(row_widget)
        row_lay.setContentsMargins(8, 6, 8, 6)
        row_lay.setSpacing(8)

        # Checkbox for marking as correct
        correct_cb = QCheckBox()
        is_written = (self.q_type_combo.currentIndex() == 2)
        if is_written:
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
            "QLineEdit { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px; font-size: 13px; color: #1e293b; }"
            "QLineEdit:focus { border: 1px solid #3b82f6; }"
        )
        row_lay.addWidget(ans_input, 1)

        # Delete button
        del_btn = QPushButton("Удалить")
        del_btn.setStyleSheet(
            "QPushButton { background-color: #fee2e2; color: #991b1b; padding: 6px 12px; border-radius: 6px; border: none; font-weight: bold; font-size: 12px; }"
            "QPushButton:hover { background-color: #fca5a5; }"
        )
        
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

        for row in self.answer_rows:
            ans_text = row["input"].text().strip()
            if ans_text:
                answers_list.append({
                    "text": ans_text,
                    "correct": True if is_written else row["cb"].isChecked()
                })

        if not answers_list:
            QMessageBox.warning(self, "Предупреждение", "Добавьте хотя бы один правильный вариант ответа!" if is_written else "Добавьте хотя бы один вариант ответа!")
            return

        if not is_written:
            correct_count = sum(1 for a in answers_list if a["correct"])
            if correct_count == 0:
                QMessageBox.warning(self, "Предупреждение", "Выберите хотя бы один правильный вариант ответа (отметьте галочкой)!")
                return

        self.question["text"] = text
        self.question["multiple"] = is_multiple
        self.question["written"] = is_written
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
            self.setWindowTitle("Мониторинг экзамена в реальном времени")
        apply_dialog_scaling(self, parent, 700, 450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Подключенные студенты ({group})" if group else "Подключенные студенты")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #1e293b; border: none;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Имя студента", "Группа", "Статус", "Результат", "Процент"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self.view_answers)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.view_answers_btn = QPushButton("Посмотреть ответы")
        self.view_answers_btn.setStyleSheet(
            "QPushButton { background-color: #3b82f6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 8px 16px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
        self.view_answers_btn.clicked.connect(self.view_answers)
        btn_layout.addWidget(self.view_answers_btn)
        
        btn_layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.setProperty("class", "secondaryBtn")
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
                status_item.setText("Сдал тест")
                status_item.setForeground(QColor("#10b981"))
            elif not s.active:
                status_item.setText("Соединение потеряно")
                status_item.setForeground(QColor("#ef4444"))
            else:
                status_item.setText("Выполняет тест")
                status_item.setForeground(QColor("#3b82f6"))

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
                grade_item.setForeground(QColor("#64748b"))


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
        self.label.setStyleSheet("font-size: 15px; color: #64748b; font-weight: bold; border: none;")
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
        self._status_label.setStyleSheet("font-size: 13px; color: #94a3b8; border: none;")
        layout.addWidget(self._status_label)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(None, "Выберите файл теста", "", "Текстовые файлы (*.txt)")
        if path:
            self.set_file(path)

    def set_file(self, path):
        self._status_label.setText(f"Выбран файл: {os.path.basename(path)}")
        self._status_label.setStyleSheet("font-size: 13px; color: #10b981; font-weight: bold; border: none;")
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
        apply_dialog_scaling(self, parent, 500, 420)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title = QLabel("Выберите тест из сохраненных:")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b; border: none; background: transparent;")
        layout.addWidget(title)
        
        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по названию или группе...")
        self.search_input.setStyleSheet(
            "QLineEdit { padding: 8px 12px; font-size: 13px; border-radius: 6px; border: 1px solid #cbd5e1; background-color: #ffffff; }"
            "QLineEdit:focus { border: 1px solid #3b82f6; }"
        )
        self.search_input.textChanged.connect(self._filter_table)
        layout.addWidget(self.search_input)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Название теста / Группа", "Вопросов"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)
        
        self._filter_table()
            
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; color: #475569; font-weight: bold; font-size: 13px; padding: 8px 16px; border: 1px solid #cbd5e1; border-radius: 6px; }"
            "QPushButton:hover { background-color: #f1f5f9; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(cancel_btn)
        
        self.select_btn = QPushButton("Выбрать")
        self.select_btn.setStyleSheet(
            "QPushButton { background-color: #3b82f6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 8px 16px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
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


