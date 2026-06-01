import json
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
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

from shared.widgets import StyledComboBox

from shared.parser import questions_to_network_payload

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
    from storage import test_path, tests_dir

class DashboardMixin:
    def _build_dashboard_page(self):
        self.dashboard_page = QWidget()
        main_layout = QVBoxLayout(self.dashboard_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем QScrollArea для адаптивной прокрутки
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Header Row
        header_lay = QHBoxLayout()
        title = QLabel("Репозиторий тестов")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("background: transparent; border: none;")
        header_lay.addWidget(title)

        header_lay.addStretch()

        create_new_btn = QPushButton("Создать новый тест")
        create_new_btn.setProperty("class", "primaryBtn")
        create_new_btn.setCursor(Qt.PointingHandCursor)
        create_new_btn.clicked.connect(self._create_new_test_flow)
        header_lay.addWidget(create_new_btn)

        import_btn = QPushButton("Импортировать тест (.txt)")
        import_btn.setProperty("class", "successBtn")
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._import_test_txt_flow)
        header_lay.addWidget(import_btn)

        layout.addLayout(header_lay)

        # Фильтры и поиск
        filter_card = QFrame()
        filter_card.setProperty("class", "card")
        filter_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 12px; }")
        filter_lay = QHBoxLayout(filter_card)
        filter_lay.setContentsMargins(16, 12, 16, 12)
        filter_lay.setSpacing(12)

        # 1. Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по названию или группе...")
        self.search_input.setStyleSheet(
            "QLineEdit { padding: 8px 12px 8px 12px; font-size: 13px; border-radius: 8px; border: 1px solid #d6d3d1; background-color: #ffffff; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )
        self.search_input.textChanged.connect(self._update_dashboard_stats)
        filter_lay.addWidget(self.search_input, 3)

        # 2. Выпадающий список статусов
        self.status_filter = StyledComboBox()
        self.status_filter.addItems(["Все статусы", "Готовые тесты", "Пустые тесты"])
        self.status_filter.setMinimumWidth(140)
        self.status_filter.setCursor(Qt.PointingHandCursor)
        self.status_filter.currentIndexChanged.connect(self._update_dashboard_stats)
        filter_lay.addWidget(self.status_filter, 1)

        # 3. Выпадающий список сортировки
        self.sort_filter = StyledComboBox()
        self.sort_filter.addItems([
            "Сортировка: По умолчанию",
            "Сортировка: Название (А-Я)",
            "Сортировка: Название (Я-А)",
            "Вопросы: Меньше -> Больше",
            "Вопросы: Больше -> Меньше"
        ])
        self.sort_filter.setMinimumWidth(180)
        self.sort_filter.setCursor(Qt.PointingHandCursor)
        self.sort_filter.currentIndexChanged.connect(self._update_dashboard_stats)
        filter_lay.addWidget(self.sort_filter, 1)

        layout.addWidget(filter_card)

        # Table of saved tests
        self.tests_table = QTableWidget(0, 3)
        self.tests_table.setHorizontalHeaderLabels(["Группа / Название", "Количество вопросов", "Статус"])
        self.tests_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tests_table.setColumnWidth(0, 450)
        self.tests_table.setColumnWidth(1, 230)
        self.tests_table.setColumnWidth(2, 150)
        self.tests_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tests_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tests_table.verticalHeader().setVisible(False)
        self.tests_table.setShowGrid(True)
        self.tests_table.setMinimumHeight(350)
        layout.addWidget(self.tests_table)

        # Action panel below the table
        act_lay = QHBoxLayout()
        act_lay.setSpacing(12)

        self.start_exam_from_repo_btn = QPushButton("Запустить тестирование")
        self.start_exam_from_repo_btn.setProperty("class", "successBtn")
        self.start_exam_from_repo_btn.setCursor(Qt.PointingHandCursor)
        self.start_exam_from_repo_btn.clicked.connect(self._start_exam_from_repo)
        act_lay.addWidget(self.start_exam_from_repo_btn)

        self.edit_test_from_repo_btn = QPushButton("Редактировать тест")
        self.edit_test_from_repo_btn.setProperty("class", "primaryBtn")
        self.edit_test_from_repo_btn.setCursor(Qt.PointingHandCursor)
        self.edit_test_from_repo_btn.clicked.connect(self._edit_test_from_repo)
        act_lay.addWidget(self.edit_test_from_repo_btn)

        self.delete_test_from_repo_btn = QPushButton("Удалить тест")
        self.delete_test_from_repo_btn.setProperty("class", "dangerBtn")
        self.delete_test_from_repo_btn.setCursor(Qt.PointingHandCursor)
        self.delete_test_from_repo_btn.clicked.connect(self._delete_test_from_repo)
        act_lay.addWidget(self.delete_test_from_repo_btn)

        act_lay.addStretch()
        layout.addLayout(act_lay)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.stacked_widget.addWidget(self.dashboard_page)

    def _get_saved_tests(self):
        tests = []
        for path in tests_dir().glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    tests.append({
                        "group": data.get("group", path.stem),
                        "questions": data.get("questions", [])
                    })
            except Exception:
                pass
        return tests

    def _update_dashboard_stats(self):
        self.tests_table.setRowCount(0)
        tests = self._get_saved_tests()

        # 1. Поиск по тексту (название теста или группы)
        if hasattr(self, "search_input"):
            search_text = self.search_input.text().strip().lower()
            if search_text:
                tests = [t for t in tests if search_text in t["group"].lower()]

        # 2. Фильтрация по статусу (Все, Готовые, Пустые)
        if hasattr(self, "status_filter"):
            status_idx = self.status_filter.currentIndex()
            if status_idx == 1: # Готовые
                tests = [t for t in tests if len(t["questions"]) > 0]
            elif status_idx == 2: # Пустые
                tests = [t for t in tests if len(t["questions"]) == 0]

        # 3. Сортировка по разным критериям
        if hasattr(self, "sort_filter"):
            sort_idx = self.sort_filter.currentIndex()
            if sort_idx == 1: # Название А-Я
                tests.sort(key=lambda x: x["group"].lower())
            elif sort_idx == 2: # Название Я-А
                tests.sort(key=lambda x: x["group"].lower(), reverse=True)
            elif sort_idx == 3: # Вопросы возрастание
                tests.sort(key=lambda x: len(x["questions"]))
            elif sort_idx == 4: # Вопросы убывание
                tests.sort(key=lambda x: len(x["questions"]), reverse=True)

        for t in tests:
            row = self.tests_table.rowCount()
            self.tests_table.insertRow(row)
            self.tests_table.setItem(row, 0, QTableWidgetItem(t["group"]))

            q_count = len(t["questions"])
            self.tests_table.setItem(row, 1, QTableWidgetItem(str(q_count)))

            status = "Готов" if q_count > 0 else "Пустой"
            status_item = QTableWidgetItem(status)
            if q_count > 0:
                status_item.setForeground(QColor("#16a34a"))
            else:
                status_item.setForeground(QColor("#dc2626"))
            self.tests_table.setItem(row, 2, status_item)

    def _create_new_test_flow(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Создать новый тест", "Введите название группы / теста:")
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

        path = test_path(group)
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
        path = test_path(group)
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
        path = test_path(self._current_test_group)
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
            old_path = test_path(self._current_test_group)
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

