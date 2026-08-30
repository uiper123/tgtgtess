from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
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
    QVBoxLayout,
    QWidget,
)

from shared.parser import parse_test_file, questions_to_network_payload
from shared.widgets import StyledComboBox

try:
    from .storage import test_path, tests_dir
    from .ui_dialogs import (
        DropZoneWidget,
        EditQuestionDialog,
        MonitoringDialog,
        SelectTestFromRepoDialog,
        StudentAnswersDialog,
    )
except ImportError:
    from storage import test_path
    from ui_dialogs import (
        EditQuestionDialog,
        SelectTestFromRepoDialog,
    )

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
        self.active_test_lbl.setStyleSheet("color: #57534e; font-size: 13px; font-weight: bold; padding: 6px 12px; background-color: #e7e5e4; border-radius: 6px; border: none;")
        top_row.addWidget(self.active_test_lbl)

        self.rename_test_btn = QPushButton("Переименовать")
        self.rename_test_btn.setProperty("class", "secondaryBtn")
        self.rename_test_btn.clicked.connect(self._rename_active_test)
        top_row.addWidget(self.rename_test_btn)

        layout.addLayout(top_row)

        # Карта кастомизации заголовков теста на клиенте
        headers_card = QFrame()
        headers_card.setStyleSheet("QFrame { background-color: #fafaf9; border: 1px dashed #d6d3d1; border-radius: 8px; }")
        hc_layout = QHBoxLayout(headers_card)
        hc_layout.setContentsMargins(16, 10, 16, 10)
        hc_layout.setSpacing(12)

        hc_title = QLabel("Заголовки на экране студента:")
        hc_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #57534e; border: none; background: transparent;")
        hc_layout.addWidget(hc_title)

        self.test_title_input = QLineEdit()
        self.test_title_input.setPlaceholderText("Главный заголовок (по умолч: Итоговое тестирование)")
        self.test_title_input.setText(self.exam_server.test_title)
        self.test_title_input.textChanged.connect(self._on_test_title_changed)
        self.test_title_input.setStyleSheet("QLineEdit { padding: 6px 10px; font-size: 12px; border: 1px solid #d6d3d1; border-radius: 6px; }")
        hc_layout.addWidget(self.test_title_input, 2)

        self.test_section_input = QLineEdit()
        self.test_section_input.setPlaceholderText("Подзаголовок (по умолч: Раздел: Основная часть)")
        self.test_section_input.setText(self.exam_server.test_section)
        self.test_section_input.textChanged.connect(self._on_test_section_changed)
        self.test_section_input.setStyleSheet("QLineEdit { padding: 6px 10px; font-size: 12px; border: 1px solid #d6d3d1; border-radius: 6px; }")
        hc_layout.addWidget(self.test_section_input, 2)

        layout.addWidget(headers_card)

        # --- Фильтр по вопросам ---
        filter_card = QFrame()
        filter_card.setObjectName("qFilterCard")
        filter_card.setStyleSheet(
            "QFrame#qFilterCard { background-color: #ffffff;"
            " border: 1px solid #e7e5e4; border-radius: 12px; }"
        )
        f_lay = QHBoxLayout(filter_card)
        f_lay.setContentsMargins(14, 10, 14, 10)
        f_lay.setSpacing(12)

        self.q_search = QLineEdit()
        self.q_search.setPlaceholderText("Поиск по тексту вопроса или варианту ответа…")
        self.q_search.setStyleSheet(
            "QLineEdit { padding: 8px 12px; font-size: 13px;"
            " border: 1px solid #e7e5e4; border-radius: 8px;"
            " background-color: #ffffff; color: #1c1917; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )
        self.q_search.textChanged.connect(self._update_questions_table)
        f_lay.addWidget(self.q_search, 3)

        self.q_type_filter = StyledComboBox()
        self.q_type_filter.addItems([
            "Все типы",
            "Одиночный выбор",
            "Множественный выбор",
            "Письменный ответ",
            "Соответствие",
        ])
        self.q_type_filter.currentIndexChanged.connect(self._update_questions_table)
        f_lay.addWidget(self.q_type_filter, 1)

        layout.addWidget(filter_card)

        # Table of Questions
        self.q_table = QTableWidget(0, 4)
        self.q_table.setHorizontalHeaderLabels(["Номер", "Текст вопроса", "Тип выбора", "Варианты ответов"])
        self.q_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.q_table.setColumnWidth(0, 80)
        self.q_table.setColumnWidth(1, 400)
        self.q_table.setColumnWidth(2, 120)
        self.q_table.setColumnWidth(3, 400)
        self.q_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.q_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.q_table.verticalHeader().setVisible(False)
        self.q_table.setShowGrid(True)
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

        # Row 2: Save / Bulk Import / Export operations
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(12)

        self.save_test_to_repo_btn = QPushButton("💾 Сохранить в репозиторий (.txt)")
        self.save_test_to_repo_btn.setProperty("class", "successBtn")
        self.save_test_to_repo_btn.setCursor(Qt.PointingHandCursor)
        self.save_test_to_repo_btn.clicked.connect(self._manual_save_active_test_to_repo)
        row2_layout.addWidget(self.save_test_to_repo_btn)

        self.import_q_from_file_btn = QPushButton("Импорт вопросов (.txt)")
        self.import_q_from_file_btn.setProperty("class", "primaryBtn")
        self.import_q_from_file_btn.clicked.connect(self.import_questions)
        row2_layout.addWidget(self.import_q_from_file_btn)

        self.import_q_from_repo_btn = QPushButton("Импорт из другого теста")
        self.import_q_from_repo_btn.setProperty("class", "secondaryBtn")
        self.import_q_from_repo_btn.clicked.connect(self._import_questions_from_repo)
        row2_layout.addWidget(self.import_q_from_repo_btn)

        self.export_test_btn = QPushButton("Экспортировать файл (.txt)")
        self.export_test_btn.setProperty("class", "secondaryBtn")
        self.export_test_btn.clicked.connect(self.export_test)
        row2_layout.addWidget(self.export_test_btn)

        row2_layout.addStretch()
        btn_box.addLayout(row2_layout)

        layout.addLayout(btn_box)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.stacked_widget.addWidget(self.questions_page)

    def _manual_save_active_test_to_repo(self):
        if not self._current_test_group or self._current_test_group == "Новый тест":
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "Сохранить тест", "Введите название теста / группы для сохранения:")
            if ok and name.strip():
                self._current_test_group = name.strip()
                self.active_test_lbl.setText(f"Активный тест: {self._current_test_group}")
                self.selected_test_sidebar_lbl.setText(f"Тест: {self._current_test_group}")
            else:
                return

        self._save_active_test_to_repo()
        if hasattr(self, "_update_dashboard_stats"):
            self._update_dashboard_stats()
        if hasattr(self, "_update_exams_page_test_view"):
            self._update_exams_page_test_view()
        self.show_toast(f"Тест '{self._current_test_group}' успешно сохранён в формате .txt", "success")

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

        query = self.q_search.text().strip().lower() if hasattr(self, "q_search") else ""
        type_idx = self.q_type_filter.currentIndex() if hasattr(self, "q_type_filter") else 0
        # 0=Все, 1=Одиночный, 2=Множественный, 3=Письменный

        for q in questions:
            q_text = q.get("text", "")
            ans_texts = [a.get("text", "") for a in q.get("answers", [])]

            # Type filter
            is_written = bool(q.get("written"))
            is_multiple = bool(q.get("multiple"))
            is_matching = bool(q.get("matching"))
            if type_idx == 1 and (is_written or is_multiple or is_matching):
                continue
            if type_idx == 2 and not is_multiple:
                continue
            if type_idx == 3 and not is_written:
                continue
            if type_idx == 4 and not is_matching:
                continue

            # Search filter (case-insensitive substring in question text or any answer)
            if query:
                haystack = (q_text + " " + " ".join(ans_texts)).lower()
                if query not in haystack:
                    continue

            row = self.q_table.rowCount()
            self.q_table.insertRow(row)

            self.q_table.setItem(row, 0, QTableWidgetItem(str(q.get("number", row + 1))))
            self.q_table.setItem(row, 1, QTableWidgetItem(q_text))

            if is_written:
                type_str = "Письменный"
            elif is_matching:
                type_str = "Соответствие"
            elif q.get("ordering"):
                type_str = "Порядок"
            elif q.get("blanks"):
                type_str = "Пропуски"
            else:
                type_str = "Множественный" if is_multiple else "Одиночный"
            self.q_table.setItem(row, 2, QTableWidgetItem(type_str))

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
            self._update_exams_page_test_view()
            self.show_toast("Вопрос успешно добавлен", "success")

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
            self._update_exams_page_test_view()
            self.show_toast(f"Вопрос №{row + 1} успешно изменён", "success")

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
        self._update_exams_page_test_view()
        self.show_toast(f"Вопрос №{row + 1} удалён", "info")

    def export_test(self):
        if not self.exam_server.questions:
            QMessageBox.warning(self, "Предупреждение", "Список вопросов пуст!")
            return

        path, _ = self._get_save_file_name(
            "Экспортировать тест",
            "",
            "Текстовые файлы (*.txt);;Все файлы (*.*)",
            default_filename="test_edited.txt",
        )
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
                    elif q.get('matching'):
                        prefix_q += " (Соответствие)"
                    elif q.get('ordering'):
                        prefix_q += " (Порядок)"
                    elif q.get('blanks'):
                        prefix_q += " (Пропуски)"
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
        path, _ = self._get_open_file_name(
            "Импортировать вопросы",
            "",
            "Текстовые файлы (*.txt);;JSON файлы (*.json);;Все файлы (*.*)",
        )
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
                self._update_exams_page_test_view()
                self.show_toast(f"Успешно импортировано {len(new_questions)} вопросов", "success")
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
                path = test_path(group)
                try:
                    if str(path).lower().endswith(".txt"):
                        new_questions = list(parse_test_file(str(path)))
                    else:
                        import json
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
                    self._update_exams_page_test_view()
                    self.show_toast(f"Импортировано {len(new_questions)} вопросов из теста '{group}'", "success")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать вопросы: {e}")

    # ========================== 3. АКТИВНЫЕ ЭКЗАМЕНЫ (ГЛАВНАЯ) ==========================
