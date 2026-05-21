"""
server/ui_server.py — Графический интерфейс преподавателя (PySide6).
Полностью рабочий Web-dashboard с вкладочной навигацией и мониторингом.
Иконки удалены, используются только понятные надписи.
"""

import os
import sys
from datetime import datetime
from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer, QSettings
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QStackedWidget, QFileDialog, QMessageBox,
    QSizePolicy, QFrame, QTextEdit, QDialog, QAbstractItemView,
    QScrollArea, QCheckBox, QComboBox, QGridLayout
)
from shared.parser import get_grade_details, questions_to_network_payload, parse_test_file

# ---------------------------------------------------------------------------
# QSS-стили под макет (Без графических иконок, аккуратные шрифты и рамки)
# ---------------------------------------------------------------------------
GLOBAL_QSS = """
* {
    font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
}
QMainWindow {
    background-color: #f8fafc;
}

/* --- Сайдбар --- */
#sidebar {
    background-color: #1e202b;
    min-width: 260px;
    max-width: 260px;
}
#sidebar QLabel#logoLabel {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
    padding: 24px 16px 4px 16px;
}
#sidebar QLabel#logoSub {
    color: #94a3b8;
    font-size: 11px;
    padding: 0 16px 20px 16px;
}
#sidebar QPushButton.navBtn {
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-radius: 8px;
    color: #cbd5e1;
    font-size: 14px;
    background: transparent;
    margin: 2px 10px;
}
#sidebar QPushButton.navBtn:hover {
    background-color: rgba(59, 130, 246, 0.15);
    color: #ffffff;
}
#sidebar QPushButton.navBtn[active="true"] {
    background-color: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    font-weight: bold;
    border-left: 4px solid #3b82f6;
    border-radius: 0px 8px 8px 0px;
    padding-left: 16px;
}
#sidebar QPushButton#createTestBtn {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px;
    border: none;
    border-radius: 10px;
    margin: 8px 14px;
}
#sidebar QPushButton#createTestBtn:hover {
    background-color: #2563eb;
}
#sidebar QLabel#serverStatus {
    color: #94a3b8;
    font-size: 12px;
    padding: 8px 18px 18px 18px;
}

/* --- Карточки --- */
QFrame.card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}
QFrame.statCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
}

/* --- Поля ввода --- */
QLineEdit {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    color: #1e293b;
}
QLineEdit:focus {
    border: 2px solid #3b82f6;
}
QSpinBox {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    color: #1e293b;
}
QSpinBox:focus {
    border: 2px solid #3b82f6;
}
QCheckBox#randomOrderCheck {
    color: #1e293b;
    font-size: 13px;
    font-weight: 600;
    spacing: 8px;
    padding: 9px 10px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background-color: #f9fafb;
}
QCheckBox#randomOrderCheck:hover {
    border-color: #3b82f6;
    background-color: #eff6ff;
}
QCheckBox#randomOrderCheck::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox#randomOrderCheck::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
}
QCheckBox#partialScoreCheck {
    color: #1e293b;
    font-size: 13px;
    font-weight: 600;
    spacing: 8px;
    padding: 9px 10px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background-color: #f9fafb;
}
QCheckBox#partialScoreCheck:hover {
    border-color: #10b981;
    background-color: #ecfdf5;
}
QCheckBox#partialScoreCheck::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox#partialScoreCheck::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
}

/* --- Кнопки --- */
QPushButton.primaryBtn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
}
QPushButton.primaryBtn:hover {
    background-color: #4f46e5;
}
QPushButton.secondaryBtn {
    background-color: #ffffff;
    color: #3b82f6;
    font-size: 13px;
    font-weight: bold;
    padding: 10px 20px;
    border: 2px solid #3b82f6;
    border-radius: 8px;
}
QPushButton.secondaryBtn:hover {
    background-color: #eff6ff;
}
QPushButton.tableSecondaryBtn {
    background-color: #ffffff;
    color: #2563eb;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 10px;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    min-height: 24px;
}
QPushButton.tableSecondaryBtn:hover {
    background-color: #eff6ff;
    border-color: #3b82f6;
}
QPushButton.dangerBtn {
    background-color: #ef4444;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
}
QPushButton.dangerBtn:hover {
    background-color: #dc2626;
}
QPushButton.tableDangerBtn {
    background-color: #fee2e2;
    color: #991b1b;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 10px;
    border: 1px solid #fca5a5;
    border-radius: 6px;
    min-height: 24px;
}
QPushButton.tableDangerBtn:hover {
    background-color: #fecaca;
}
QPushButton.successBtn {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
}
QPushButton.successBtn:hover {
    background-color: #059669;
}

/* --- Таблицы --- */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    gridline-color: transparent;
    font-size: 13px;
    color: #334155;
}
QTableWidget::item {
    border-bottom: 1px solid #f1f5f9;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    font-weight: bold;
    font-size: 12px;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    text-align: left;
}

/* --- Зона сброса файлов --- */
#dropZone {
    background-color: #ffffff;
    border: 2px dashed #cbd5e1;
    border-radius: 16px;
    min-height: 140px;
}
#dropZone:hover {
    border-color: #3b82f6;
    background-color: #f0f7ff;
}

/* --- Лог --- */
QTextEdit#logArea {
    background-color: #1e293b;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 10px;
}

/* --- Заголовки --- */
QLabel.sectionTitle {
    font-size: 20px;
    font-weight: bold;
    color: #1e293b;
}
QLabel.sectionSub {
    font-size: 13px;
    color: #64748b;
}

/* --- Dialogs & QMessageBox --- */
QDialog {
    background-color: #ffffff;
}
QDialog QLabel {
    color: #1e293b;
    font-size: 13px;
    background: transparent;
}
QDialog QLineEdit {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1e293b;
    font-size: 13px;
}
QDialog QLineEdit:focus {
    border-color: #3b82f6;
}
QDialog QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 18px;
    border: none;
    border-radius: 8px;
    min-width: 80px;
}
QDialog QPushButton:hover {
    background-color: #2563eb;
}
QMessageBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
}
QMessageBox QLabel {
    color: #1e293b;
    font-size: 14px;
}
QMessageBox QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
}
QMessageBox QPushButton:hover {
    background-color: #2563eb;
}
"""

# ---------------------------------------------------------------------------
# Диалоги ответов студента и редактирования вопросов
# ---------------------------------------------------------------------------
class StudentAnswersDialog(QDialog):
    def __init__(self, student, questions, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ответы студента: {student.name}")
        self.resize(700, 500)
        self.setStyleSheet(GLOBAL_QSS)

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
                sel_lbl = QLabel(f"Выбрано студентом: {', '.join(student_ans) if student_ans else '[Нет ответа]'}")
                sel_lbl.setWordWrap(True)
                sel_lbl.setStyleSheet("font-size: 12px; color: #475569; border: none;")
                card_lay.addWidget(sel_lbl)

                # Correct answers
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
        self.resize(650, 600)
        self.setStyleSheet(GLOBAL_QSS)
        
        self.question = question if question else {
            "number": 1,
            "text": "",
            "multiple": False,
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

        # Multiple choice checkbox
        self.multiple_cb = QCheckBox("Множественный выбор (несколько правильных ответов)")
        self.multiple_cb.setChecked(self.question.get("multiple", False))
        self.multiple_cb.setCursor(Qt.PointingHandCursor)
        self.multiple_cb.setStyleSheet(
            "QCheckBox {"
            "  color: #1e293b;"
            "  font-size: 13px;"
            "  font-weight: 600;"
            "  spacing: 10px;"
            "  background-color: #f1f5f9;"
            "  border: 1px solid #cbd5e1;"
            "  border-radius: 8px;"
            "  padding: 10px 14px;"
            "}"
            "QCheckBox:hover {"
            "  background-color: #e2e8f0;"
            "  border-color: #94a3b8;"
            "}"
            "QCheckBox:checked {"
            "  background-color: #eff6ff;"
            "  border-color: #3b82f6;"
            "  color: #1e3a8a;"
            "}"
        )
        layout.addWidget(self.multiple_cb)

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
        lbl2 = QLabel("Варианты ответов:")
        lbl2.setStyleSheet("color: #1e293b; font-size: 13px; font-weight: bold; border: none; background: transparent;")
        layout.addWidget(lbl2)
        
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
        self._load_answers()

    def _load_answers(self):
        for ans in self.question.get("answers", []):
            self._create_answer_row(ans.get("text", ""), ans.get("correct", False))

    def _create_answer_row(self, text="", is_correct=False):
        row_widget = QWidget()
        row_widget.setStyleSheet("QWidget { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; }")
        row_lay = QHBoxLayout(row_widget)
        row_lay.setContentsMargins(8, 6, 8, 6)
        row_lay.setSpacing(8)

        # Checkbox for marking as correct
        correct_cb = QCheckBox()
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
        for row in self.answer_rows:
            ans_text = row["input"].text().strip()
            if ans_text:
                answers_list.append({
                    "text": ans_text,
                    "correct": row["cb"].isChecked()
                })

        if not answers_list:
            QMessageBox.warning(self, "Предупреждение", "Добавьте хотя бы один вариант ответа!")
            return

        self.question["text"] = text
        self.question["multiple"] = self.multiple_cb.isChecked()
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
        self.resize(700, 450)
        self.setStyleSheet(GLOBAL_QSS)

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
        self.setWindowTitle("Выбрать тест из репозитория")
        self.resize(500, 400)
        self.setStyleSheet(GLOBAL_QSS)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        title = QLabel("Выберите тест из сохраненных:")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b; border: none; background: transparent;")
        layout.addWidget(title)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Название теста / Группа", "Вопросов"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        layout.addWidget(self.table)
        
        for t in tests:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(t["group"]))
            self.table.setItem(row, 1, QTableWidgetItem(str(len(t["questions"]))))
            
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
        
    def accept(self):
        selected = self.table.currentRow()
        if selected >= 0:
            self.selected_group = self.table.item(selected, 0).text()
            super().accept()
        else:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тест!")


# ---------------------------------------------------------------------------
# Главное окно Преподавателя
# ---------------------------------------------------------------------------
class ServerWindow(QMainWindow):
    def __init__(self, exam_server, parent=None):
        super().__init__(parent)
        self.exam_server = exam_server
        self._settings = QSettings("EduTest", "Server")
        self.setWindowTitle("TTGTiSO-Test — Панель преподавателя")
        
        # Установка иконки приложения
        from PySide6.QtGui import QIcon
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "image.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setMinimumSize(1200, 750)
        self.resize(1300, 850)
        self.setStyleSheet(GLOBAL_QSS)

        self._current_test_group = "Новый тест"

        # Подключение сигналов сервера
        self.exam_server.log_message.connect(self._append_log)
        self.exam_server.server_error.connect(self._show_error)
        self.exam_server.student_connected.connect(self._on_student_connected)
        self.exam_server.student_finished.connect(self._on_student_finished)
        self.exam_server.server_started.connect(self._on_server_started)

        self._build_ui()

    def _get_disable_delete_confirm(self) -> bool:
        val = self._settings.value("disable_delete_confirm", False)
        if val is None:
            return False
        if isinstance(val, str):
            return val.lower() in ('true', '1')
        if isinstance(val, int):
            return val != 0
        return bool(val)

    def _get_open_file_name(self, title: str, directory: str, filter_str: str) -> tuple:
        return QFileDialog.getOpenFileName(None, title, directory, filter_str)

    def _get_save_file_name(self, title: str, directory: str, filter_str: str) -> tuple:
        return QFileDialog.getSaveFileName(None, title, directory, filter_str)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Боковое меню (Сайдбар) ---
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        logo = QLabel("TTGTiSO-Test")
        logo.setObjectName("logoLabel")
        sb_layout.addWidget(logo)

        sub = QLabel("ПОРТАЛ ПРЕПОДАВАТЕЛЯ")
        sub.setObjectName("logoSub")
        sb_layout.addWidget(sub)

        # Индикатор выбранного теста в сайдбаре
        self.selected_test_sidebar_lbl = QLabel("Тест: Новый тест")
        self.selected_test_sidebar_lbl.setObjectName("sidebarSelectedTest")
        self.selected_test_sidebar_lbl.setStyleSheet(
            "QLabel {"
            "  color: #34d399;"
            "  font-size: 12px;"
            "  font-weight: bold;"
            "  margin: 4px 16px 12px 16px;"
            "  padding: 8px 12px;"
            "  background-color: rgba(52, 211, 153, 0.1);"
            "  border-radius: 6px;"
            "  border: 1px solid rgba(52, 211, 153, 0.2);"
            "}"
        )
        sb_layout.addWidget(self.selected_test_sidebar_lbl)

        sb_layout.addSpacing(10)

        # Кнопки навигации (Без иконок)
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Все тесты"),
            ("exams", "Активные экзамены"),
            ("results", "Результаты студентов"),
            ("settings", "Настройки")
        ]

        for code, label in nav_items:
            btn = QPushButton(label)
            btn.setProperty("class", "navBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("active", "false")
            btn.clicked.connect(lambda checked=False, c=code: self.switch_page(c))
            self.nav_buttons[code] = btn
            sb_layout.addWidget(btn)

        sb_layout.addStretch()

        self._status_label = QLabel("Сервер: Выключен")
        self._status_label.setObjectName("serverStatus")
        sb_layout.addWidget(self._status_label)

        root_layout.addWidget(sidebar)

        # --- Главная зона (QStackedWidget) ---
        self.stacked_widget = QStackedWidget()
        root_layout.addWidget(self.stacked_widget, 1)

        self._build_dashboard_page()
        self._build_questions_page()
        self._build_exams_page()
        self._build_results_page()
        self._build_settings_page()

        # Активная страница по умолчанию
        self.switch_page("exams")

    def switch_page(self, code):
        """Переключение страниц интерфейса."""
        highlight_code = "dashboard" if code == "questions" else code
        for c, btn in self.nav_buttons.items():
            btn.setProperty("active", "true" if c == highlight_code else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        if code == "dashboard":
            self._update_dashboard_stats()
            self.stacked_widget.setCurrentWidget(self.dashboard_page)
        elif code == "questions":
            self._update_questions_table()
            self.stacked_widget.setCurrentWidget(self.questions_page)
        elif code == "exams":
            self.stacked_widget.setCurrentWidget(self.exams_page)
        elif code == "results":
            self._update_results_table()
            self.stacked_widget.setCurrentWidget(self.results_page)
        elif code == "settings":
            self.stacked_widget.setCurrentWidget(self.settings_page)

    # ========================== 1. ДАШБОРД ==========================
    # ========================== 1. РЕПОЗИТОРИЙ ТЕСТОВ ==========================
    def _build_dashboard_page(self):
        self.dashboard_page = QWidget()
        layout = QVBoxLayout(self.dashboard_page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header Row
        header_lay = QHBoxLayout()
        title = QLabel("Репозиторий тестов")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b; border: none; background: transparent;")
        header_lay.addWidget(title)
        
        header_lay.addStretch()
        
        create_new_btn = QPushButton("Создать новый тест")
        create_new_btn.setStyleSheet(
            "QPushButton { background-color: #3b82f6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
        create_new_btn.clicked.connect(self._create_new_test_flow)
        header_lay.addWidget(create_new_btn)

        import_btn = QPushButton("Импортировать тест (.txt)")
        import_btn.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        import_btn.clicked.connect(self._import_test_txt_flow)
        header_lay.addWidget(import_btn)
        
        layout.addLayout(header_lay)

        # Table of saved tests
        self.tests_table = QTableWidget(0, 3)
        self.tests_table.setHorizontalHeaderLabels(["Академическая группа / Название", "Количество вопросов", "Статус"])
        self.tests_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tests_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tests_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tests_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tests_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tests_table.verticalHeader().setVisible(False)
        self.tests_table.setShowGrid(False)
        layout.addWidget(self.tests_table)

        # Action panel below the table
        act_lay = QHBoxLayout()
        act_lay.setSpacing(12)

        self.start_exam_from_repo_btn = QPushButton("Запустить экзамен")
        self.start_exam_from_repo_btn.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.start_exam_from_repo_btn.clicked.connect(self._start_exam_from_repo)
        act_lay.addWidget(self.start_exam_from_repo_btn)

        self.edit_test_from_repo_btn = QPushButton("Редактировать тест")
        self.edit_test_from_repo_btn.setStyleSheet(
            "QPushButton { background-color: #8b5cf6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #7c3aed; }"
        )
        self.edit_test_from_repo_btn.clicked.connect(self._edit_test_from_repo)
        act_lay.addWidget(self.edit_test_from_repo_btn)

        self.delete_test_from_repo_btn = QPushButton("Удалить тест")
        self.delete_test_from_repo_btn.setStyleSheet(
            "QPushButton { background-color: #fee2e2; color: #991b1b; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #fca5a5; }"
        )
        self.delete_test_from_repo_btn.clicked.connect(self._delete_test_from_repo)
        act_lay.addWidget(self.delete_test_from_repo_btn)

        act_lay.addStretch()
        layout.addLayout(act_lay)

        self.stacked_widget.addWidget(self.dashboard_page)

    def _get_saved_tests(self):
        import glob
        import json
        os.makedirs("tests", exist_ok=True)
        tests = []
        for path in glob.glob("tests/*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tests.append({
                        "group": data.get("group", os.path.basename(path).replace(".json", "")),
                        "questions": data.get("questions", [])
                    })
            except Exception:
                pass
        return tests

    def _update_dashboard_stats(self):
        self.tests_table.setRowCount(0)
        tests = self._get_saved_tests()
        for t in tests:
            row = self.tests_table.rowCount()
            self.tests_table.insertRow(row)
            self.tests_table.setItem(row, 0, QTableWidgetItem(t["group"]))
            
            q_count = len(t["questions"])
            self.tests_table.setItem(row, 1, QTableWidgetItem(str(q_count)))
            
            status = "Готов" if q_count > 0 else "Пустой"
            status_item = QTableWidgetItem(status)
            if q_count > 0:
                status_item.setForeground(QColor("#10b981"))
            else:
                status_item.setForeground(QColor("#ef4444"))
            self.tests_table.setItem(row, 2, status_item)

    def _create_new_test_flow(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Создать новый тест", "Введите название академической группы / теста:")
        if ok and name.strip():
            name = name.strip()
            self._current_test_group = name
            self.exam_server._questions = []
            self.exam_server._network_payload = []
            self.exam_server.test_title = "Итоговое тестирование"
            self.exam_server.test_section = "Раздел: Основная часть"
            self._update_test_headers_inputs()
            self.active_test_lbl.setText(f"Активный тест: {name}")
            self.selected_test_sidebar_lbl.setText(f"Тест: {name}")
            self._save_active_test_to_repo()
            self._update_dashboard_stats()
            self._update_exams_page_test_view()
            self.switch_page("questions")
            QMessageBox.information(self, "Успешно", f"Создан новый тест для группы '{name}'. Добавьте вопросы в открывшемся окне редактора!")

    def _import_test_txt_flow(self):
        path, _ = self._get_open_file_name("Импортировать тест", "", "Текстовые файлы (*.txt)")
        if path:
            try:
                count = self.exam_server.load_test(path)
                group_name = os.path.basename(path).replace(".txt", "").replace(".json", "")
                self._current_test_group = group_name
                self._update_test_headers_inputs()
                self.active_test_lbl.setText(f"Активный тест: {group_name}")
                self.selected_test_sidebar_lbl.setText(f"Тест: {group_name}")
                self._save_active_test_to_repo()
                self._update_dashboard_stats()
                self._update_exams_page_test_view()
                
                QMessageBox.information(self, "Успешно", f"Тест успешно импортирован во 'Все тесты' под именем '{group_name}' ({count} вопросов).")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать файл: {e}")

    def _start_exam_from_repo(self):
        selected = self.tests_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тест из таблицы!")
            return
        group = self.tests_table.item(selected, 0).text()
        self._load_test_from_repo_by_group(group)
        self.switch_page("exams")

    def _edit_test_from_repo(self):
        selected = self.tests_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тест из таблицы!")
            return
        group = self.tests_table.item(selected, 0).text()
        self._load_test_from_repo_by_group(group)
        self.switch_page("questions")

    def _delete_test_from_repo(self):
        selected = self.tests_table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите тест из таблицы!")
            return
        group = self.tests_table.item(selected, 0).text()
        disable_confirm = self._get_disable_delete_confirm()
        if not disable_confirm:
            reply = QMessageBox.question(
                self, "Удаление теста", 
                f"Вы уверены, что хотите безвозвратно удалить тест для группы '{group}'?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        if True:
            path = os.path.join("tests", f"{group}.json")
            if os.path.exists(path):
                try:
                    os.remove(path)
                    self.exam_server.log_message.emit(f"Тест '{group}' удален из репозитория.")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить файл: {e}")
            
            # If the deleted test was the active one, clear active questions
            if self._current_test_group == group:
                self._current_test_group = "Новый тест"
                self.exam_server._questions = []
                self.exam_server._network_payload = []
                self.exam_server.test_title = "Итоговое тестирование"
                self.exam_server.test_section = "Раздел: Основная часть"
                self._update_test_headers_inputs()
                self.active_test_lbl.setText("Активный тест: Новый тест")
                self.selected_test_sidebar_lbl.setText("Тест: Новый тест")
            
            self._update_dashboard_stats()
            self._update_exams_page_test_view()

    def _load_test_from_repo_by_group(self, group):
        import json
        path = os.path.join("tests", f"{group}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.exam_server._questions = data.get("questions", [])
                    self.exam_server._network_payload = questions_to_network_payload(self.exam_server._questions)
                    self.exam_server.test_title = data.get("title", "Итоговое тестирование")
                    self.exam_server.test_section = data.get("section", "Раздел: Основная часть")
                    self._update_test_headers_inputs()
                    self._current_test_group = group
                    self.active_test_lbl.setText(f"Активный тест: {group}")
                    self.selected_test_sidebar_lbl.setText(f"Тест: {group}")
                    self.exam_server.log_message.emit(f"Загружен тест для группы '{group}' из репозитория.")
                    self._update_exams_page_test_view()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл теста: {e}")

    def _save_active_test_to_repo(self):
        if not self._current_test_group or self._current_test_group == "Новый тест" or not self.exam_server.questions:
            return
        os.makedirs("tests", exist_ok=True)
        import json
        path = os.path.join("tests", f"{self._current_test_group}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "group": self._current_test_group,
                    "title": self.exam_server.test_title,
                    "section": self.exam_server.test_section,
                    "questions": self.exam_server.questions
                }, f, ensure_ascii=False, indent=2)
            self.exam_server.log_message.emit(f"Тест для группы '{self._current_test_group}' автосохранен в репозиторий.")
        except Exception as e:
            self.exam_server.log_message.emit(f"Ошибка автосохранения теста: {e}")

    def _rename_active_test(self):
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Переименовать тест / группу", "Введите новое название для теста / группы:", text=self._current_test_group)
        if ok and new_name.strip():
            new_name = new_name.strip()
            old_path = os.path.join("tests", f"{self._current_test_group}.json")
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass
            self._current_test_group = new_name
            self.active_test_lbl.setText(f"Активный тест: {new_name}")
            self.selected_test_sidebar_lbl.setText(f"Тест: {new_name}")
            self._save_active_test_to_repo()
            self._update_dashboard_stats()
            self._update_exams_page_test_view()
            QMessageBox.information(self, "Успешно", f"Тест переименован в '{new_name}'")

    def _build_questions_page(self):
        self.questions_page = QWidget()
        layout = QVBoxLayout(self.questions_page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Top layout with Title and active test status
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        back_btn = QPushButton("← Назад")
        back_btn.setStyleSheet(
            "QPushButton { background-color: #f1f5f9; color: #475569; font-size: 12px; font-weight: bold; padding: 6px 14px; border: 1px solid #cbd5e1; border-radius: 6px; }"
            "QPushButton:hover { background-color: #e2e8f0; color: #1e293b; }"
        )
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(lambda: self.switch_page("dashboard"))
        top_row.addWidget(back_btn)

        title = QLabel("Список загруженных вопросов")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b; border: none; background: transparent;")
        top_row.addWidget(title)
        
        top_row.addStretch()
        
        self.active_test_lbl = QLabel("Активный тест: Новый тест")
        self.active_test_lbl.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold; padding: 6px 12px; background-color: #e2e8f0; border-radius: 6px; border: none;")
        top_row.addWidget(self.active_test_lbl)
        
        self.rename_test_btn = QPushButton("Переименовать")
        self.rename_test_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; color: #3b82f6; font-size: 12px; font-weight: bold; padding: 6px 12px; border: 1px solid #3b82f6; border-radius: 6px; }"
            "QPushButton:hover { background-color: #eff6ff; }"
        )
        self.rename_test_btn.clicked.connect(self._rename_active_test)
        top_row.addWidget(self.rename_test_btn)
        
        layout.addLayout(top_row)

        # Карта кастомизации заголовков теста на клиенте
        headers_card = QFrame()
        headers_card.setStyleSheet("QFrame { background-color: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 8px; }")
        hc_layout = QHBoxLayout(headers_card)
        hc_layout.setContentsMargins(16, 10, 16, 10)
        hc_layout.setSpacing(12)

        hc_title = QLabel("Заголовки на экране студента:")
        hc_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #475569; border: none; background: transparent;")
        hc_layout.addWidget(hc_title)

        self.test_title_input = QLineEdit()
        self.test_title_input.setPlaceholderText("Главный заголовок (по умолч: Итоговое тестирование)")
        self.test_title_input.setText(self.exam_server.test_title)
        self.test_title_input.textChanged.connect(self._on_test_title_changed)
        self.test_title_input.setStyleSheet("QLineEdit { padding: 6px 10px; font-size: 12px; border: 1px solid #cbd5e1; border-radius: 4px; }")
        hc_layout.addWidget(self.test_title_input, 2)

        self.test_section_input = QLineEdit()
        self.test_section_input.setPlaceholderText("Подзаголовок (по умолч: Раздел: Основная часть)")
        self.test_section_input.setText(self.exam_server.test_section)
        self.test_section_input.textChanged.connect(self._on_test_section_changed)
        self.test_section_input.setStyleSheet("QLineEdit { padding: 6px 10px; font-size: 12px; border: 1px solid #cbd5e1; border-radius: 4px; }")
        hc_layout.addWidget(self.test_section_input, 2)

        layout.addWidget(headers_card)

        # Table of Questions
        self.q_table = QTableWidget(0, 4)
        self.q_table.setHorizontalHeaderLabels(["Номер", "Текст вопроса", "Тип выбора", "Варианты ответов"])
        self.q_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.q_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.q_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.q_table.verticalHeader().setVisible(False)
        self.q_table.setShowGrid(False)
        self.q_table.doubleClicked.connect(self.edit_question)
        layout.addWidget(self.q_table)

        # Action Buttons Layout (2-row responsive design to prevent squishing)
        btn_box = QVBoxLayout()
        btn_box.setSpacing(10)

        # Row 1: Question CRUD operations
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)

        self.add_q_btn = QPushButton("Добавить вопрос")
        self.add_q_btn.setStyleSheet(
            "QPushButton { background-color: #8b5cf6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #7c3aed; }"
        )
        self.add_q_btn.clicked.connect(self.add_question)
        row1_layout.addWidget(self.add_q_btn)

        self.edit_q_btn = QPushButton("Редактировать вопрос")
        self.edit_q_btn.setStyleSheet(
            "QPushButton { background-color: #3b82f6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #2563eb; }"
        )
        self.edit_q_btn.clicked.connect(self.edit_question)
        row1_layout.addWidget(self.edit_q_btn)

        self.del_q_btn = QPushButton("Удалить вопрос")
        self.del_q_btn.setStyleSheet(
            "QPushButton { background-color: #ef4444; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #dc2626; }"
        )
        self.del_q_btn.clicked.connect(self.delete_question)
        row1_layout.addWidget(self.del_q_btn)

        row1_layout.addStretch()
        btn_box.addLayout(row1_layout)

        # Row 2: Bulk Import / Export operations
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(12)

        self.import_q_from_file_btn = QPushButton("Импорт вопросов (.txt)")
        self.import_q_from_file_btn.setStyleSheet(
            "QPushButton { background-color: #f59e0b; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #d97706; }"
        )
        self.import_q_from_file_btn.clicked.connect(self.import_questions)
        row2_layout.addWidget(self.import_q_from_file_btn)

        self.import_q_from_repo_btn = QPushButton("Импорт из другого теста")
        self.import_q_from_repo_btn.setStyleSheet(
            "QPushButton { background-color: #6366f1; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #4f46e5; }"
        )
        self.import_q_from_repo_btn.clicked.connect(self._import_questions_from_repo)
        row2_layout.addWidget(self.import_q_from_repo_btn)

        self.export_test_btn = QPushButton("Экспортировать тест (.txt)")
        self.export_test_btn.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 18px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        self.export_test_btn.clicked.connect(self.export_test)
        row2_layout.addWidget(self.export_test_btn)

        row2_layout.addStretch()
        btn_box.addLayout(row2_layout)

        layout.addLayout(btn_box)
        self.stacked_widget.addWidget(self.questions_page)

    def _on_test_title_changed(self, text):
        self.exam_server.test_title = text.strip() if text.strip() else "Итоговое тестирование"
        self._save_active_test_to_repo()

    def _on_test_section_changed(self, text):
        self.exam_server.test_section = text.strip() if text.strip() else "Раздел: Основная часть"
        self._save_active_test_to_repo()

    def _update_test_headers_inputs(self):
        if hasattr(self, 'test_title_input') and hasattr(self, 'test_section_input'):
            self.test_title_input.blockSignals(True)
            self.test_title_input.setText(self.exam_server.test_title)
            self.test_title_input.blockSignals(False)

            self.test_section_input.blockSignals(True)
            self.test_section_input.setText(self.exam_server.test_section)
            self.test_section_input.blockSignals(False)

    def _update_questions_table(self):
        self.q_table.setRowCount(0)
        questions = self.exam_server.questions
        for q in questions:
            row = self.q_table.rowCount()
            self.q_table.insertRow(row)

            self.q_table.setItem(row, 0, QTableWidgetItem(str(q.get('number', row + 1))))
            self.q_table.setItem(row, 1, QTableWidgetItem(q.get('text', '')))

            type_str = "Множественный" if q.get('multiple') else "Одиночный"
            self.q_table.setItem(row, 2, QTableWidgetItem(type_str))

            ans_texts = [a.get('text', '') for a in q.get('answers', [])]
            self.q_table.setItem(row, 3, QTableWidgetItem(", ".join(ans_texts)))

    def add_question(self):
        dlg = EditQuestionDialog(None, self)
        if dlg.exec():
            new_q = dlg.question
            new_q["number"] = len(self.exam_server.questions) + 1
            self.exam_server.questions.append(new_q)
            self.exam_server._network_payload = questions_to_network_payload(self.exam_server.questions)
            self._update_questions_table()
            self._save_active_test_to_repo()
            self._update_dashboard_stats()
            self._update_exams_page_test_view()

    def edit_question(self):
        row = self.q_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите вопрос для редактирования!")
            return
        
        q = self.exam_server.questions[row]
        import copy
        q_copy = copy.deepcopy(q)
        
        dlg = EditQuestionDialog(q_copy, self)
        if dlg.exec():
            self.exam_server.questions[row] = dlg.question
            self.exam_server._network_payload = questions_to_network_payload(self.exam_server.questions)
            self._update_questions_table()
            self._save_active_test_to_repo()
            self._update_dashboard_stats()
            self._update_exams_page_test_view()

    def delete_question(self):
        row = self.q_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Предупреждение", "Пожалуйста, выберите вопрос для удаления!")
            return
        
        disable_confirm = self._get_disable_delete_confirm()
        if not disable_confirm:
            reply = QMessageBox.question(
                self, "Удаление вопроса", 
                f"Вы уверены, что хотите удалить вопрос №{row + 1}?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.exam_server.questions.pop(row)
        for idx, q in enumerate(self.exam_server.questions):
            q["number"] = idx + 1
        self.exam_server._network_payload = questions_to_network_payload(self.exam_server.questions)
        self._update_questions_table()
        self._save_active_test_to_repo()
        self._update_dashboard_stats()
        self._update_exams_page_test_view()

    def export_test(self):
        if not self.exam_server.questions:
            QMessageBox.warning(self, "Предупреждение", "Список вопросов пуст!")
            return
        
        path, _ = self._get_save_file_name("Экспортировать тест", "test_edited.txt", "Текстовые файлы (*.txt)")
        if path:
            if not path.lower().endswith('.txt'):
                path += '.txt'
            try:
                lines = []
                lines.append(f"@title: {self.exam_server.test_title}")
                lines.append(f"@section: {self.exam_server.test_section}")
                lines.append("")
                
                for q in self.exam_server.questions:
                    prefix_q = "?"
                    if q.get('multiple'):
                        prefix_q += " (С множественным выбором)"
                    lines.append(f"{prefix_q} {q.get('text', '')}")
                    if q.get('image_data'):
                        lines.append(f"@image_base64: {q.get('image_data')}")
                    for ans in q.get('answers', []):
                        prefix = "+" if ans.get('correct') else "-"
                        lines.append(f"{prefix} {ans.get('text', '')}")
                    lines.append("")
                
                with open(path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                
                QMessageBox.information(self, "Успешно", f"Тест успешно сохранен в файл:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить тест: {e}")

    def import_questions(self):
        path, _ = self._get_open_file_name("Импортировать вопросы", "", "Текстовые файлы (*.txt)")
        if path:
            try:
                new_questions = parse_test_file(path)
                start_idx = len(self.exam_server.questions)
                for i, q in enumerate(new_questions):
                    q["number"] = start_idx + i + 1
                    self.exam_server.questions.append(q)
                self.exam_server._network_payload = questions_to_network_payload(self.exam_server.questions)
                self._update_questions_table()
                self._save_active_test_to_repo()
                self._update_dashboard_stats()
                self._update_exams_page_test_view()
                QMessageBox.information(self, "Успешно", f"Успешно импортировано {len(new_questions)} вопросов.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать вопросы: {e}")

    def _import_questions_from_repo(self):
        tests = self._get_saved_tests()
        # Exclude current test
        tests = [t for t in tests if t["group"] != self._current_test_group]
        if not tests:
            QMessageBox.information(self, "Информация", "Нет других сохранённых тестов для импорта.")
            return
        dlg = SelectTestFromRepoDialog(tests, self)
        dlg.setWindowTitle("Импортировать вопросы из другого теста")
        if dlg.exec():
            group = dlg.selected_group
            if group:
                import json
                path = os.path.join("tests", f"{group}.json")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    new_questions = data.get("questions", [])
                    start_idx = len(self.exam_server.questions)
                    for i, q in enumerate(new_questions):
                        q["number"] = start_idx + i + 1
                        self.exam_server.questions.append(q)
                    self.exam_server._network_payload = questions_to_network_payload(self.exam_server.questions)
                    self._update_questions_table()
                    self._save_active_test_to_repo()
                    self._update_dashboard_stats()
                    self._update_exams_page_test_view()
                    QMessageBox.information(self, "Успешно", f"Импортировано {len(new_questions)} вопросов из теста '{group}'.")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать вопросы: {e}")

    # ========================== 3. АКТИВНЫЕ ЭКЗАМЕНЫ (ГЛАВНАЯ) ==========================
    def _build_exams_page(self):
        self.exams_page = QWidget()
        layout = QVBoxLayout(self.exams_page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Управление экзаменами")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Загрузите тест, настройте академическую группу и запустите сервер")
        subtitle.setProperty("class", "sectionSub")
        layout.addWidget(subtitle)

        # Карточка настроек
        settings_card = QFrame()
        settings_card.setProperty("class", "card")
        sc_layout = QVBoxLayout(settings_card)
        sc_layout.setContentsMargins(24, 20, 24, 20)
        sc_layout.setSpacing(16)

        # Row 0: Inputs
        inputs_layout = QHBoxLayout()
        inputs_layout.setSpacing(16)

        grp_col = QVBoxLayout()
        grp_label = QLabel("Академическая группа / Класс")
        grp_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        grp_col.addWidget(grp_label)
        self._group_input = QLineEdit()
        self._group_input.setPlaceholderText("Например: CS-101")
        grp_col.addWidget(self._group_input)
        inputs_layout.addLayout(grp_col, 4)

        dur_col = QVBoxLayout()
        dur_label = QLabel("Лимит времени (минуты)")
        dur_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        dur_col.addWidget(dur_label)
        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(1, 300)
        self._duration_spin.setValue(60)
        self._duration_spin.setButtonSymbols(QSpinBox.NoButtons)
        dur_col.addWidget(self._duration_spin)
        inputs_layout.addLayout(dur_col, 1)

        # Выбор количества вопросов
        limit_col = QVBoxLayout()
        limit_label = QLabel("Кол-во вопросов")
        limit_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        limit_col.addWidget(limit_label)
        self._questions_limit_spin = QSpinBox()
        self._questions_limit_spin.setRange(1, 1000)
        self._questions_limit_spin.setValue(10)
        self._questions_limit_spin.setButtonSymbols(QSpinBox.NoButtons)
        limit_col.addWidget(self._questions_limit_spin)
        inputs_layout.addLayout(limit_col, 1)

        # Количество попыток для одного ФИО
        attempts_col = QVBoxLayout()
        attempts_label = QLabel("Попыток")
        attempts_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        attempts_col.addWidget(attempts_label)
        self._attempts_limit_spin = QSpinBox()
        self._attempts_limit_spin.setRange(1, 10)
        self._attempts_limit_spin.setValue(1)
        self._attempts_limit_spin.setButtonSymbols(QSpinBox.NoButtons)
        attempts_col.addWidget(self._attempts_limit_spin)
        inputs_layout.addLayout(attempts_col, 1)

        sc_layout.addLayout(inputs_layout)

        # Row 1: Checkboxes and Action Button
        options_layout = QHBoxLayout()
        options_layout.setSpacing(16)

        rnd_col = QVBoxLayout()
        rnd_label = QLabel("Случайный порядок")
        rnd_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        rnd_col.addWidget(rnd_label)
        self._random_order_cb = QCheckBox("Случайный порядок")
        self._random_order_cb.setObjectName("randomOrderCheck")
        self._random_order_cb.setCursor(Qt.PointingHandCursor)
        rnd_col.addWidget(self._random_order_cb)
        options_layout.addLayout(rnd_col, 1)

        # Частичный зачёт множественных вопросов
        partial_col = QVBoxLayout()
        partial_label = QLabel("Проверка ответов")
        partial_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        partial_col.addWidget(partial_label)
        self._partial_multiple_cb = QCheckBox("Частичные ответы")
        self._partial_multiple_cb.setObjectName("partialScoreCheck")
        self._partial_multiple_cb.setChecked(True)
        self._partial_multiple_cb.setCursor(Qt.PointingHandCursor)
        partial_col.addWidget(self._partial_multiple_cb)
        options_layout.addLayout(partial_col, 1)

        btn_col = QVBoxLayout()
        btn_label = QLabel("")  # Spacer label to align button vertically
        btn_label.setStyleSheet("font-size: 12px;")
        btn_col.addWidget(btn_label)
        self._start_btn = QPushButton("Запустить экзамен")
        self._start_btn.setProperty("class", "successBtn")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setMinimumHeight(44)
        self._start_btn.clicked.connect(self._toggle_exam)
        btn_col.addWidget(self._start_btn)
        options_layout.addLayout(btn_col, 2)

        sc_layout.addLayout(options_layout)

        layout.addWidget(settings_card)

        # Контейнер выбора теста (скрывается, если тест выбран)
        self.test_selector_widget = QWidget()
        sel_layout = QVBoxLayout(self.test_selector_widget)
        sel_layout.setContentsMargins(0, 0, 0, 0)
        sel_layout.setSpacing(12)

        repo_btn_layout = QHBoxLayout()
        self.choose_from_repo_btn = QPushButton("Выбрать тест из сохраненных в репозитории")
        self.choose_from_repo_btn.setStyleSheet(
            "QPushButton { background-color: #8b5cf6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 20px; border: none; border-radius: 8px; }"
            "QPushButton:hover { background-color: #7c3aed; }"
        )
        self.choose_from_repo_btn.clicked.connect(self._choose_test_from_repo_dialog)
        repo_btn_layout.addWidget(self.choose_from_repo_btn)
        repo_btn_layout.addStretch()
        sel_layout.addLayout(repo_btn_layout)

        # Зона сброса
        self._drop_zone = DropZoneWidget()
        self._drop_zone.file_dropped.connect(self._on_file_dropped)
        sel_layout.addWidget(self._drop_zone)
        
        layout.addWidget(self.test_selector_widget)

        # Карточка активного готового теста (показывается, если тест выбран)
        self.active_test_status_card = QFrame()
        self.active_test_status_card.setObjectName("activeTestStatusCard")
        self.active_test_status_card.setStyleSheet(
            "QFrame#activeTestStatusCard {"
            "  background-color: #ecfdf5;"
            "  border: 1px solid #a7f3d0;"
            "  border-radius: 12px;"
            "}"
        )
        card_lay = QHBoxLayout(self.active_test_status_card)
        card_lay.setContentsMargins(20, 16, 20, 16)
        card_lay.setSpacing(16)

        info_col = QVBoxLayout()
        self.active_test_title_lbl = QLabel("Тест готов к запуску:")
        self.active_test_title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #065f46; border: none; background: transparent;")
        info_col.addWidget(self.active_test_title_lbl)

        self.active_test_questions_lbl = QLabel("Вопросов: 0")
        self.active_test_questions_lbl.setStyleSheet("font-size: 13px; color: #047857; border: none; background: transparent;")
        info_col.addWidget(self.active_test_questions_lbl)
        card_lay.addLayout(info_col, 1)

        self.change_test_btn = QPushButton("Сменить тест")
        self.change_test_btn.setStyleSheet(
            "QPushButton { background-color: #ffffff; color: #065f46; font-weight: bold; font-size: 13px; padding: 8px 16px; border: 1px solid #a7f3d0; border-radius: 6px; }"
            "QPushButton:hover { background-color: #f0fdf4; }"
        )
        self.change_test_btn.clicked.connect(self._show_test_selector)
        card_lay.addWidget(self.change_test_btn)

        layout.addWidget(self.active_test_status_card)
        self.active_test_status_card.hide()

        # Таблица экзаменов
        table_title = QLabel("Список активных экзаменов")
        table_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e293b;")
        layout.addWidget(table_title)

        self._exam_table = QTableWidget(0, 5)
        self._exam_table.setHorizontalHeaderLabels(
            ["Название теста", "Группа", "Статус", "Студенты", "Мониторинг"]
        )
        self._exam_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._exam_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._exam_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._exam_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._exam_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._exam_table.verticalHeader().setDefaultSectionSize(44)
        self._exam_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._exam_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._exam_table.verticalHeader().setVisible(False)
        self._exam_table.setShowGrid(False)
        self._exam_table.setMinimumHeight(140)
        layout.addWidget(self._exam_table)

        # Лог событий
        self._log = QTextEdit()
        self._log.setObjectName("logArea")
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(130)
        layout.addWidget(self._log)

        self._loaded_test_name = ""
        self._student_count = 0
        self._update_exams_page_test_view()
        self.stacked_widget.addWidget(self.exams_page)

    def _update_exams_page_test_view(self):
        if self._current_test_group and self._current_test_group != "Новый тест" and self.exam_server.questions:
            total_q = len(self.exam_server.questions)
            self.active_test_title_lbl.setText(f"Тест готов к запуску: {self._current_test_group}")
            self.active_test_questions_lbl.setText(f"Количество вопросов: {total_q}")
            self._questions_limit_spin.setRange(1, total_q)
            self._questions_limit_spin.setValue(total_q)
            self.active_test_status_card.show()
            self.test_selector_widget.hide()
        else:
            self.active_test_status_card.hide()
            self.test_selector_widget.show()

    def _show_test_selector(self):
        self.active_test_status_card.hide()
        self.test_selector_widget.show()

    def _choose_test_from_repo_dialog(self):
        tests = self._get_saved_tests()
        if not tests:
            QMessageBox.information(self, "Информация", "В репозитории пока нет сохраненных тестов. Создайте новый тест во вкладке 'Все тесты' или перетащите файл теста!")
            return
        
        dlg = SelectTestFromRepoDialog(tests, self)
        if dlg.exec():
            group = dlg.selected_group
            if group:
                self._load_test_from_repo_by_group(group)

    @Slot(str)
    def _on_file_dropped(self, path: str):
        try:
            count = self.exam_server.load_test(path)
            self._loaded_test_name = os.path.basename(path)
            
            group_name = os.path.basename(path).replace(".txt", "").replace(".json", "")
            self._current_test_group = group_name
            self._update_test_headers_inputs()
            self.active_test_lbl.setText(f"Активный тест: {group_name}")
            self.selected_test_sidebar_lbl.setText(f"Тест: {group_name}")
            self._save_active_test_to_repo()
            self._update_dashboard_stats()
            
            self.exam_server.log_message.emit(f"Тест успешно импортирован в репозиторий под именем '{group_name}'")
        except Exception as e:
            self._show_error(str(e))

    def _toggle_exam(self):
        group = self._group_input.text().strip()
        if not group:
            self._show_error("Укажите академическую группу!")
            return
        if not self.exam_server.questions:
            self._show_error("Сначала перетащите или выберите файл теста!")
            return
        
        # Проверяем, не запущен ли уже тест для этой группы
        if group.lower() in self.exam_server._active_exams:
            self._show_error(f"Экзамен для группы '{group}' уже запущен!")
            return

        duration = self._duration_spin.value()
        
        # Запускаем экзамен на сервере
        questions = list(self.exam_server.questions)
        limit = self._questions_limit_spin.value()

        self.exam_server.start_exam(
            group=group,
            duration=duration,
            questions=questions,
            title=self.exam_server.test_title,
            section=self.exam_server.test_section,
            test_name=self._current_test_group if self._current_test_group else (self._loaded_test_name if self._loaded_test_name else "Тест"),
            partial_multiple=self._partial_multiple_cb.isChecked(),
            random_order=self._random_order_cb.isChecked(),
            max_attempts=self._attempts_limit_spin.value(),
            questions_limit=limit,
        )

        # Обновляем надпись статуса сервера
        port = self.exam_server._tcp_server.serverPort()
        self._status_label.setText(f"Сервер: Работает (порт {port})")
        self._status_label.setStyleSheet("color: #10b981; font-weight: bold;")

        # Перезаполняем таблицу активных экзаменов
        self._update_exam_table_view()

    def _update_exam_table_view(self):
        self._exam_table.setRowCount(0)
        for group_key, exam in list(self.exam_server._active_exams.items()):
            row = self._exam_table.rowCount()
            self._exam_table.insertRow(row)
            
            # Название теста
            self._exam_table.setItem(row, 0, QTableWidgetItem(exam['test_name']))
            # Группа
            self._exam_table.setItem(row, 1, QTableWidgetItem(exam['group']))
            # Статус
            self._exam_table.setItem(row, 2, QTableWidgetItem("Активен"))
            
            # Подсчёт студентов для этой группы
            student_count = sum(1 for s in self.exam_server._students.values() if s.group.lower() == group_key)
            self._exam_table.setItem(row, 3, QTableWidgetItem(str(student_count)))

            # Кнопки действий (Мониторинг и Остановить)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(8)

            monitor_btn = QPushButton("Мониторинг")
            monitor_btn.setProperty("class", "tableSecondaryBtn")
            monitor_btn.setCursor(Qt.PointingHandCursor)
            monitor_btn.clicked.connect(lambda checked=False, g=exam['group']: self._open_monitoring_for_group(g))
            actions_layout.addWidget(monitor_btn)

            stop_btn = QPushButton("Остановить")
            stop_btn.setProperty("class", "tableDangerBtn")
            stop_btn.setCursor(Qt.PointingHandCursor)
            stop_btn.clicked.connect(lambda checked=False, g=exam['group']: self._stop_exam_for_group(g))
            actions_layout.addWidget(stop_btn)

            self._exam_table.setCellWidget(row, 4, actions_widget)

    def _open_monitoring_for_group(self, group):
        dlg = MonitoringDialog(self.exam_server, group=group, parent=self)
        dlg.exec()

    def _stop_exam_for_group(self, group):
        self.exam_server.stop_exam_for_group(group)
        self._update_exam_table_view()
        
        # Если больше нет активных экзаменов, сбрасываем статус сервера
        if not self.exam_server.is_active:
            self._status_label.setText("Сервер: Выключен")
            self._status_label.setStyleSheet("color: #94a3b8;")

    @Slot(str, int)
    def _on_server_started(self, addr, port):
        self._status_label.setText(f"Сервер: Работает (порт {port})")
        self._status_label.setStyleSheet("color: #10b981; font-weight: bold;")
        self._update_exam_table_view()

    def _open_monitoring(self):
        dlg = MonitoringDialog(self.exam_server, parent=self)
        dlg.exec()

    # ========================== 4. РЕЗУЛЬТАТЫ СТУДЕНТОВ ==========================
    def _build_results_page(self):
        self.results_page = QWidget()
        layout = QVBoxLayout(self.results_page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Итоговые результаты студентов")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1e293b; border: none;")
        layout.addWidget(title)

        # Filters and Search Layout
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        # Search box
        self.r_search = QLineEdit()
        self.r_search.setPlaceholderText("🔍 Поиск по ФИО студента...")
        self.r_search.setStyleSheet("QLineEdit { padding: 8px 12px; font-size: 13px; }")
        self.r_search.textChanged.connect(self._update_results_table)
        filter_layout.addWidget(self.r_search, 2)

        # Group Filter
        self.r_group_filter = QComboBox()
        self.r_group_filter.setStyleSheet("QComboBox { padding: 8px 12px; font-size: 13px; min-width: 150px; }")
        self.r_group_filter.currentIndexChanged.connect(self._update_results_table)
        filter_layout.addWidget(self.r_group_filter, 1)

        # Sort combo
        self.r_sort_filter = QComboBox()
        self.r_sort_filter.addItems([
            "По умолчанию",
            "Имя (А-Я)",
            "Имя (Я-А)",
            "Группа",
            "Процент (По убыванию)",
            "Процент (По возрастанию)"
        ])
        self.r_sort_filter.setStyleSheet("QComboBox { padding: 8px 12px; font-size: 13px; min-width: 180px; }")
        self.r_sort_filter.currentIndexChanged.connect(self._update_results_table)
        filter_layout.addWidget(self.r_sort_filter, 1)

        layout.addLayout(filter_layout)

        # Table of Results
        self.r_table = QTableWidget(0, 5)
        self.r_table.setHorizontalHeaderLabels(["Имя студента", "Группа", "Набранные баллы", "Процент", "Время сдачи"])
        self.r_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.r_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.r_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.r_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.r_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.r_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.r_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.r_table.verticalHeader().setVisible(False)
        self.r_table.setShowGrid(False)
        layout.addWidget(self.r_table)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Экспортировать отфильтрованные в CSV")
        export_btn.setStyleSheet(
            "QPushButton { background-color: #10b981; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 20px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #059669; }"
        )
        export_btn.clicked.connect(self._export_manually)
        btn_row.addWidget(export_btn)
        
        clear_btn = QPushButton("Очистить всю историю результатов")
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #ef4444; color: #ffffff; font-weight: bold; font-size: 13px; padding: 10px 20px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #dc2626; }"
        )
        clear_btn.clicked.connect(self._clear_results_history)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.stacked_widget.addWidget(self.results_page)

    def _clear_results_history(self):
        reply = QMessageBox.question(
            self, "Очистить историю результатов",
            "Вы уверены, что хотите безвозвратно удалить всю сохраненную историю результатов студентов?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.exam_server.clear_all_results()
            self._update_results_table()
            QMessageBox.information(self, "Успешно", "История результатов успешно очищена.")

    def _refresh_group_filter_list(self):
        self.r_group_filter.blockSignals(True)
        current = self.r_group_filter.currentText()
        self.r_group_filter.clear()
        self.r_group_filter.addItem("Все группы")
        
        # Collect all unique groups
        groups = sorted(list(set(r.get('group', '') for r in self.exam_server.results if r.get('group'))))
        self.r_group_filter.addItems(groups)
        
        idx = self.r_group_filter.findText(current)
        if idx >= 0:
            self.r_group_filter.setCurrentIndex(idx)
        else:
            self.r_group_filter.setCurrentIndex(0)
        self.r_group_filter.blockSignals(False)

    def _update_results_table(self):
        self._refresh_group_filter_list()
        self.r_table.setRowCount(0)
        results = list(self.exam_server.results)
        
        # 1. Apply search filter
        search_text = self.r_search.text().strip().lower()
        if search_text:
            results = [r for r in results if search_text in r.get('name', '').lower()]

        # 2. Apply group filter
        group_filter = self.r_group_filter.currentText()
        if group_filter and group_filter != "Все группы":
            results = [r for r in results if r.get('group') == group_filter]

        # 3. Apply sorting
        sort_type = self.r_sort_filter.currentText()
        if sort_type == "Имя (А-Я)":
            results.sort(key=lambda x: x.get('name', '').lower())
        elif sort_type == "Имя (Я-А)":
            results.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
        elif sort_type == "Группа":
            results.sort(key=lambda x: x.get('group', '').lower())
        elif sort_type == "Процент (По убыванию)":
            def get_percent(res):
                try:
                    parts = res.get('score', '0/0').split('/')
                    return float(parts[0]) / float(parts[1]) if float(parts[1]) > 0 else 0
                except Exception:
                    return 0
            results.sort(key=get_percent, reverse=True)
        elif sort_type == "Процент (По возрастанию)":
            def get_percent(res):
                try:
                    parts = res.get('score', '0/0').split('/')
                    return float(parts[0]) / float(parts[1]) if float(parts[1]) > 0 else 0
                except Exception:
                    return 0
            results.sort(key=get_percent)

        self.filtered_results = results

        # 4. Fill the table
        for r in results:
            row = self.r_table.rowCount()
            self.r_table.insertRow(row)
            self.r_table.setItem(row, 0, QTableWidgetItem(r.get('name', '')))
            self.r_table.setItem(row, 1, QTableWidgetItem(r.get('group', '')))
            
            score_str = r.get('score', '0/0')
            self.r_table.setItem(row, 2, QTableWidgetItem(score_str))
            
            grade_text, grade_color = get_grade_details(score_str)
            grade_item = QTableWidgetItem(grade_text)
            grade_item.setForeground(QColor(grade_color))
            self.r_table.setItem(row, 3, grade_item)
            
            self.r_table.setItem(row, 4, QTableWidgetItem(r.get('timestamp', '')))

    def _export_manually(self):
        if not hasattr(self, 'filtered_results') or not self.filtered_results:
            QMessageBox.warning(self, "Предупреждение", "Нет результатов для экспорта!")
            return
        
        path, _ = self._get_save_file_name("Экспортировать отфильтрованные результаты", "results_filtered.csv", "CSV-файлы (*.csv)")
        if path:
            if not path.lower().endswith('.csv'):
                path += '.csv'
            import csv
            try:
                with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.DictWriter(f, fieldnames=['name', 'group', 'score', 'timestamp'])
                    writer.writeheader()
                    for r in self.filtered_results:
                        writer.writerow({
                            'name': r.get('name', ''),
                            'group': r.get('group', ''),
                            'score': r.get('score', ''),
                            'timestamp': r.get('timestamp', '')
                        })
                QMessageBox.information(self, "Успешно", f"Отфильтрованные результаты успешно сохранены:\n{path}")
            except IOError as exc:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать результаты: {exc}")

    # ========================== 5. НАСТРОЙКИ СИСТЕМЫ ==========================
    def _build_settings_page(self):
        self.settings_page = QWidget()
        layout = QVBoxLayout(self.settings_page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Настройки системы")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        form = QFrame()
        form.setProperty("class", "card")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(12)

        lbl_port = QLabel("Порт TCP-сервера")
        lbl_port.setStyleSheet("font-size: 13px; font-weight: bold; color: #64748b;")
        form_layout.addWidget(lbl_port)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(self._settings.value("tcp_port", 9876, type=int))
        self.port_spin.setMaximumWidth(180)
        form_layout.addWidget(self.port_spin)
        
        self.disable_delete_confirm_cb = QCheckBox("Отключить подтверждение удаления для вопросов и теста")
        self.disable_delete_confirm_cb.setObjectName("randomOrderCheck")
        self.disable_delete_confirm_cb.setCursor(Qt.PointingHandCursor)
        self.disable_delete_confirm_cb.setMaximumWidth(500)
        self.disable_delete_confirm_cb.setChecked(self._get_disable_delete_confirm())
        self.disable_delete_confirm_cb.toggled.connect(self._on_confirm_cb_toggled)
        form_layout.addWidget(self.disable_delete_confirm_cb)

        save_btn = QPushButton("Применить настройки")
        save_btn.setProperty("class", "primaryBtn")
        save_btn.clicked.connect(self._save_settings)
        form_layout.addWidget(save_btn, 0, Qt.AlignLeft)

        layout.addWidget(form)
        layout.addStretch()
        self.stacked_widget.addWidget(self.settings_page)

    def _on_confirm_cb_toggled(self, checked):
        self._settings.setValue("disable_delete_confirm", checked)
        self._settings.sync()

    def _save_settings(self):
        new_port = self.port_spin.value()
        disable_confirm = self.disable_delete_confirm_cb.isChecked()
        self.exam_server.DEFAULT_PORT = new_port
        self._settings.setValue("tcp_port", new_port)
        self._settings.setValue("disable_delete_confirm", disable_confirm)
        self._settings.sync()
        QMessageBox.information(self, "Настройки", f"Настройки успешно сохранены.\nПорт TCP-сервера: {new_port}")

    # ========================== СИГНАЛЫ И ХЕЛПЕРЫ ==========================

    @Slot(str, str)
    def _on_student_connected(self, name, group):
        self._update_exam_table_view()

    @Slot(str, str, str)
    def _on_student_finished(self, name, group, score):
        self._update_exam_table_view()

    @Slot(str)
    def _append_log(self, msg: str):
        ts = datetime.now().strftime('%H:%M:%S')
        self._log.append(f"[{ts}] {msg}")

    @Slot(str)
    def _show_error(self, msg: str):
        self._append_log(f"ОШИБКА: {msg}")
        QMessageBox.warning(self, "Ошибка", msg)
