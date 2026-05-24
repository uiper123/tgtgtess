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
except ImportError:
    from ui_dialogs import (
        StudentAnswersDialog, EditQuestionDialog, MonitoringDialog,
        DropZoneWidget, SelectTestFromRepoDialog
    )

class ExamsMixin:
    def _build_exams_page(self):
        self.exams_page = QWidget()
        main_layout = QVBoxLayout(self.exams_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем QScrollArea для адаптивной прокрутки главной страницы управления
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Управление экзаменами")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Загрузите тест")
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
        grp_label = QLabel("Группа")
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
        self._duration_spin.setValue(self._settings.value("default_duration", 60, type=int))
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
        self._questions_limit_spin.setValue(self._settings.value("default_questions_limit", 10, type=int))
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
        self._attempts_limit_spin.setValue(self._settings.value("default_attempts", 1, type=int))
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
        self._random_order_cb.setChecked(self._settings.value("default_random_order", False, type=bool))
        rnd_col.addWidget(self._random_order_cb)
        options_layout.addLayout(rnd_col, 1)

        # Частичный зачёт множественных вопросов
        partial_col = QVBoxLayout()
        partial_label = QLabel("Проверка ответов")
        partial_label.setStyleSheet("font-size: 12px; color: #64748b; font-weight: bold;")
        partial_col.addWidget(partial_label)
        self._partial_multiple_cb = QCheckBox("Частичные ответы")
        self._partial_multiple_cb.setObjectName("partialScoreCheck")
        self._partial_multiple_cb.setChecked(self._settings.value("default_partial_multiple", True, type=bool))
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
        self.choose_from_repo_btn.setCursor(Qt.PointingHandCursor)
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
        self._exam_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Interactive)
        self._exam_table.setColumnWidth(4, 240)
        self._exam_table.verticalHeader().setDefaultSectionSize(54)
        self._exam_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._exam_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._exam_table.verticalHeader().setVisible(False)
        self._exam_table.setShowGrid(False)
        self._exam_table.setMinimumHeight(160)
        layout.addWidget(self._exam_table)

        # Лог событий
        self._log = QTextEdit()
        self._log.setObjectName("logArea")
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(120)
        layout.addWidget(self._log)

        self._loaded_test_name = ""
        self._student_count = 0
        self._update_exams_page_test_view()

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.stacked_widget.addWidget(self.exams_page)

    def _update_exams_page_test_view(self):
        if self._current_test_group and self._current_test_group != "Новый тест" and self.exam_server.questions:
            total_q = len(self.exam_server.questions)
            self.active_test_title_lbl.setText(f"Тест готов к запуску: {self._current_test_group}")
            self.active_test_questions_lbl.setText(f"Количество вопросов: {total_q}")
            self._questions_limit_spin.setRange(1, total_q)
            self._questions_limit_spin.setValue(min(self._settings.value("default_questions_limit", 10, type=int), total_q))
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
        if group.lower() in self.exam_server.get_active_exams():
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
        for group_key, exam in self.exam_server.get_active_exams().items():
            row = self._exam_table.rowCount()
            self._exam_table.insertRow(row)
            
            # Название теста
            self._exam_table.setItem(row, 0, QTableWidgetItem(exam['test_name']))
            # Группа
            self._exam_table.setItem(row, 1, QTableWidgetItem(exam['group']))
            # Статус
            self._exam_table.setItem(row, 2, QTableWidgetItem("Активен"))
            
            # Подсчёт студентов для этой группы
            student_count = sum(1 for s in self.exam_server.get_connected_students() if s.group.lower() == group_key)
            self._exam_table.setItem(row, 3, QTableWidgetItem(str(student_count)))

            # Кнопки действий (Мониторинг и Остановить)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
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
