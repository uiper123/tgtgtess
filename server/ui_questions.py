import os
import json
from datetime import datetime
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox,
    QSizePolicy, QFrame, QTextEdit, QAbstractItemView,
    QScrollArea, QCheckBox, QComboBox, QGridLayout
)
from shared.parser import get_grade_details, questions_to_network_payload, parse_test_file

try:
    from .ui_dialogs import (
        StudentAnswersDialog, EditQuestionDialog, MonitoringDialog,
        DropZoneWidget, SelectTestFromRepoDialog
    )
    from .storage import test_path, tests_dir
except ImportError:
    from ui_dialogs import (
        StudentAnswersDialog, EditQuestionDialog, MonitoringDialog,
        DropZoneWidget, SelectTestFromRepoDialog
    )
    from storage import test_path, tests_dir

class QuestionsMixin:
    def _build_questions_page(self):
        self.questions_page = QWidget()
        main_layout = QVBoxLayout(self.questions_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем QScrollArea для предотвращения обрезки таблицы вопросов и кнопок действий
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Top layout with Title and active test status
        top_row = QHBoxLayout()
        top_row.setSpacing(16)

        back_btn = QPushButton("← Назад")
        back_btn.setProperty("class", "secondaryBtn")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(lambda: self.switch_page("dashboard"))
        top_row.addWidget(back_btn)

        title = QLabel("Список загруженных вопросов")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("background: transparent; border: none;")
        top_row.addWidget(title)
        
        top_row.addStretch()
        
        self.active_test_lbl = QLabel("Активный тест: Новый тест")
        self.active_test_lbl.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold; padding: 6px 12px; background-color: #e2e8f0; border-radius: 6px; border: none;")
        top_row.addWidget(self.active_test_lbl)
        
        self.rename_test_btn = QPushButton("Переименовать")
        self.rename_test_btn.setProperty("class", "secondaryBtn")
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
        self.test_title_input.setStyleSheet("QLineEdit { padding: 6px 10px; font-size: 12px; border: 1px solid #cbd5e1; border-radius: 6px; }")
        hc_layout.addWidget(self.test_title_input, 2)

        self.test_section_input = QLineEdit()
        self.test_section_input.setPlaceholderText("Подзаголовок (по умолч: Раздел: Основная часть)")
        self.test_section_input.setText(self.exam_server.test_section)
        self.test_section_input.textChanged.connect(self._on_test_section_changed)
        self.test_section_input.setStyleSheet("QLineEdit { padding: 6px 10px; font-size: 12px; border: 1px solid #cbd5e1; border-radius: 6px; }")
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
        self.q_table.setMinimumHeight(350)
        self.q_table.doubleClicked.connect(self.edit_question)
        layout.addWidget(self.q_table)

        # Action Buttons Layout (2-row responsive design to prevent squishing)
        btn_box = QVBoxLayout()
        btn_box.setSpacing(10)

        # Row 1: Question CRUD operations
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(12)

        self.add_q_btn = QPushButton("Добавить вопрос")
        self.add_q_btn.setProperty("class", "successBtn")
        self.add_q_btn.clicked.connect(self.add_question)
        row1_layout.addWidget(self.add_q_btn)

        self.edit_q_btn = QPushButton("Редактировать вопрос")
        self.edit_q_btn.setProperty("class", "primaryBtn")
        self.edit_q_btn.clicked.connect(self.edit_question)
        row1_layout.addWidget(self.edit_q_btn)

        self.del_q_btn = QPushButton("Удалить вопрос")
        self.del_q_btn.setProperty("class", "dangerBtn")
        self.del_q_btn.clicked.connect(self.delete_question)
        row1_layout.addWidget(self.del_q_btn)

        row1_layout.addStretch()
        btn_box.addLayout(row1_layout)

        # Row 2: Bulk Import / Export operations
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(12)

        self.import_q_from_file_btn = QPushButton("Импорт вопросов (.txt)")
        self.import_q_from_file_btn.setProperty("class", "primaryBtn")
        self.import_q_from_file_btn.clicked.connect(self.import_questions)
        row2_layout.addWidget(self.import_q_from_file_btn)

        self.import_q_from_repo_btn = QPushButton("Импорт из другого теста")
        self.import_q_from_repo_btn.setProperty("class", "primaryBtn")
        self.import_q_from_repo_btn.clicked.connect(self._import_questions_from_repo)
        row2_layout.addWidget(self.import_q_from_repo_btn)

        self.export_test_btn = QPushButton("Экспортировать тест (.txt)")
        self.export_test_btn.setProperty("class", "successBtn")
        self.export_test_btn.clicked.connect(self.export_test)
        row2_layout.addWidget(self.export_test_btn)

        row2_layout.addStretch()
        btn_box.addLayout(row2_layout)

        layout.addLayout(btn_box)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
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

            if q.get('written'):
                type_str = "Письменный"
            else:
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
                    if q.get('written'):
                        prefix_q += " (Письменный ответ)"
                    elif q.get('multiple'):
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
                path = test_path(group)
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
