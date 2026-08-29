import os

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from shared.widgets import StyledComboBox

try:
    from .ui_dialogs import (
        DropZoneWidget,
        EditQuestionDialog,
        MonitoringDialog,
        SelectTestFromRepoDialog,
        StudentAnswersDialog,
    )
except ImportError:
    pass

class SettingsMixin:
    def _build_settings_page(self):
        self.settings_page = QWidget()
        main_layout = QVBoxLayout(self.settings_page)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем QScrollArea для удобной прокрутки настроек
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        title = QLabel("Настройки системы")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        # Вспомогательный метод для стилизации рядов настроек
        def add_form_row(grid_layout, label_text, widget, row_idx):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 13px; font-weight: 500; color: #57534e; background: transparent;")
            widget.setMaximumWidth(140)
            grid_layout.addWidget(lbl, row_idx, 0, Qt.AlignLeft | Qt.AlignVCenter)
            grid_layout.addWidget(widget, row_idx, 1, Qt.AlignLeft | Qt.AlignVCenter)

        # ----------------------------------------------------
        # СЕКЦИЯ 1: Сетевые настройки и приложение
        # ----------------------------------------------------
        sect1_card = QFrame()
        sect1_card.setProperty("class", "card")
        s1_layout = QVBoxLayout(sect1_card)
        s1_layout.setContentsMargins(20, 20, 20, 20)
        s1_layout.setSpacing(14)

        s1_title = QLabel("Основные параметры сервера и безопасности")
        s1_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #292524;")
        s1_layout.addWidget(s1_title)

        # Порт
        port_lay = QHBoxLayout()
        lbl_port = QLabel("Порт TCP-сервера:")
        lbl_port.setStyleSheet("font-size: 13px; font-weight: 500; color: #57534e; background: transparent;")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(self._settings.value("tcp_port", 9876, type=int))
        self.port_spin.setMaximumWidth(140)
        port_lay.addWidget(lbl_port)
        port_lay.addWidget(self.port_spin)
        port_lay.addStretch()
        s1_layout.addLayout(port_lay)

        # Подтверждение удаления
        self.disable_delete_confirm_cb = QCheckBox("Отключить диалоги подтверждения при удалении вопросов и тестов")
        self.disable_delete_confirm_cb.setCursor(Qt.PointingHandCursor)
        self.disable_delete_confirm_cb.setChecked(self._get_disable_delete_confirm())
        s1_layout.addWidget(self.disable_delete_confirm_cb)

        # Автоэкспорт в Excel (.xlsx)
        self.auto_export_csv_cb = QCheckBox("Автоматически экспортировать результаты в Excel (.xlsx) при остановке тестирования")
        self.auto_export_csv_cb.setCursor(Qt.PointingHandCursor)
        self.auto_export_csv_cb.setChecked(self._settings.value("auto_export_xlsx", self._settings.value("auto_export_csv", True, type=bool), type=bool))
        s1_layout.addWidget(self.auto_export_csv_cb)

        # Всплывающие уведомления
        self.show_notifications_cb = QCheckBox("Показывать всплывающие уведомления (сохранение, запуск тестов)")
        self.show_notifications_cb.setCursor(Qt.PointingHandCursor)
        self.show_notifications_cb.setChecked(self._settings.value("show_notifications", True, type=bool))
        s1_layout.addWidget(self.show_notifications_cb)

        layout.addWidget(sect1_card)

        # ----------------------------------------------------
        # СЕКЦИЯ: Директория хранения и загрузки тестов
        # ----------------------------------------------------
        sect_dir_card = QFrame()
        sect_dir_card.setProperty("class", "card")
        sd_layout = QVBoxLayout(sect_dir_card)
        sd_layout.setContentsMargins(20, 20, 20, 20)
        sd_layout.setSpacing(12)

        sd_title = QLabel("Директория хранения и загрузки тестов")
        sd_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #292524;")
        sd_layout.addWidget(sd_title)

        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)

        try:
            from .storage import default_tests_dir, tests_dir
        except ImportError:
            from storage import default_tests_dir, tests_dir

        self.tests_dir_input = QLineEdit()
        self.tests_dir_input.setText(str(tests_dir()))
        self.tests_dir_input.setReadOnly(True)
        self.tests_dir_input.setStyleSheet("padding: 8px 10px; font-size: 13px;")
        dir_row.addWidget(self.tests_dir_input, 1)

        self.browse_tests_dir_btn = QPushButton("Обзор...")
        self.browse_tests_dir_btn.setProperty("class", "primaryBtn")
        self.browse_tests_dir_btn.setCursor(Qt.PointingHandCursor)
        self.browse_tests_dir_btn.clicked.connect(self._browse_tests_dir)
        dir_row.addWidget(self.browse_tests_dir_btn)

        self.open_tests_dir_btn = QPushButton("Открыть папку")
        self.open_tests_dir_btn.setProperty("class", "secondaryBtn")
        self.open_tests_dir_btn.setCursor(Qt.PointingHandCursor)
        self.open_tests_dir_btn.clicked.connect(self._open_current_tests_dir)
        dir_row.addWidget(self.open_tests_dir_btn)

        self.reset_tests_dir_btn = QPushButton("По умолчанию")
        self.reset_tests_dir_btn.setProperty("class", "secondaryBtn")
        self.reset_tests_dir_btn.setCursor(Qt.PointingHandCursor)
        self.reset_tests_dir_btn.clicked.connect(self._reset_tests_dir)
        dir_row.addWidget(self.reset_tests_dir_btn)

        sd_layout.addLayout(dir_row)
        layout.addWidget(sect_dir_card)

        # ----------------------------------------------------
        # СЕКЦИЯ 2: Параметры запуска тестирования по умолчанию
        # ----------------------------------------------------
        sect2_card = QFrame()
        sect2_card.setProperty("class", "card")
        s2_layout = QVBoxLayout(sect2_card)
        s2_layout.setContentsMargins(20, 20, 20, 20)
        s2_layout.setSpacing(14)

        s2_title = QLabel("Параметры запуска тестирований по умолчанию")
        s2_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #292524;")
        s2_layout.addWidget(s2_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        # Время по умолчанию
        self.def_duration_spin = QSpinBox()
        self.def_duration_spin.setRange(1, 300)
        self.def_duration_spin.setValue(self._settings.value("default_duration", 60, type=int))
        add_form_row(grid, "Лимит времени по умолчанию (минуты):", self.def_duration_spin, 0)

        # Вопросы по умолчанию
        self.def_q_limit_spin = QSpinBox()
        self.def_q_limit_spin.setRange(1, 1000)
        self.def_q_limit_spin.setValue(self._settings.value("default_questions_limit", 10, type=int))
        add_form_row(grid, "Количество вопросов по умолчанию:", self.def_q_limit_spin, 1)

        # Попытки по умолчанию
        self.def_attempts_spin = QSpinBox()
        self.def_attempts_spin.setRange(1, 10)
        self.def_attempts_spin.setValue(self._settings.value("default_attempts", 1, type=int))
        add_form_row(grid, "Количество попыток по умолчанию:", self.def_attempts_spin, 2)

        s2_layout.addLayout(grid)

        # Галочки
        self.def_random_order_cb = QCheckBox("Перемешивать порядок вопросов у студентов по умолчанию")
        self.def_random_order_cb.setCursor(Qt.PointingHandCursor)
        self.def_random_order_cb.setChecked(self._settings.value("default_random_order", False, type=bool))
        s2_layout.addWidget(self.def_random_order_cb)

        self.def_shuffle_answers_cb = QCheckBox("Перемешивать варианты ответов у студентов по умолчанию")
        self.def_shuffle_answers_cb.setCursor(Qt.PointingHandCursor)
        self.def_shuffle_answers_cb.setChecked(self._settings.value("default_shuffle_answers", False, type=bool))
        s2_layout.addWidget(self.def_shuffle_answers_cb)

        self.def_partial_cb = QCheckBox("Разрешить частичный зачет баллов для множественного выбора по умолчанию")
        self.def_partial_cb.setCursor(Qt.PointingHandCursor)
        self.def_partial_cb.setChecked(self._settings.value("default_partial_multiple", True, type=bool))
        s2_layout.addWidget(self.def_partial_cb)

        layout.addWidget(sect2_card)

        # ----------------------------------------------------
        # СЕКЦИЯ 3: Критерии успеваемости (пороговые значения)
        # ----------------------------------------------------
        sect3_card = QFrame()
        sect3_card.setProperty("class", "card")
        s3_layout = QVBoxLayout(sect3_card)
        s3_layout.setContentsMargins(20, 20, 20, 20)
        s3_layout.setSpacing(14)

        s3_title = QLabel("Цветовая индикация результатов (пороговые проценты)")
        s3_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #292524;")
        s3_layout.addWidget(s3_title)

        grid3 = QGridLayout()
        grid3.setSpacing(12)

        # Порог отлично (зеленый)
        self.g5_spin = QSpinBox()
        self.g5_spin.setRange(1, 100)
        self.g5_spin.setValue(self._settings.value("grade_5_min", 90, type=int))
        add_form_row(grid3, "Отлично / Высокий результат (Зеленый) от %:", self.g5_spin, 0)

        # Порог хорошо (синий)
        self.g4_spin = QSpinBox()
        self.g4_spin.setRange(1, 100)
        self.g4_spin.setValue(self._settings.value("grade_4_min", 70, type=int))
        add_form_row(grid3, "Хорошо / Средний результат (Синий) от %:", self.g4_spin, 1)

        # Порог удовл (желтый)
        self.g3_spin = QSpinBox()
        self.g3_spin.setRange(1, 100)
        self.g3_spin.setValue(self._settings.value("grade_3_min", 50, type=int))
        add_form_row(grid3, "Удовлетворительно / Минимальный зачет (Желтый) от %:", self.g3_spin, 2)

        s3_layout.addLayout(grid3)
        layout.addWidget(sect3_card)

        # ----------------------------------------------------
        # СЕКЦИЯ 4: Внешний вид и масштабирование
        # ----------------------------------------------------
        sect4_card = QFrame()
        sect4_card.setProperty("class", "card")
        s4_layout = QVBoxLayout(sect4_card)
        s4_layout.setContentsMargins(20, 20, 20, 20)
        s4_layout.setSpacing(14)

        s4_title = QLabel("Внешний вид и масштабирование")
        s4_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #292524;")
        s4_layout.addWidget(s4_title)

        grid4 = QGridLayout()
        grid4.setSpacing(12)

        self.scale_combo = StyledComboBox()
        self.scale_combo.addItems(["80%", "100%", "125%", "150%", "175%", "200%"])

        saved_scale = self._settings.value("ui_scale", "100%")
        if isinstance(saved_scale, float):
            saved_scale = f"{int(saved_scale * 100)}%"
        elif isinstance(saved_scale, str) and not saved_scale.endswith("%"):
            try:
                saved_scale = f"{int(float(saved_scale) * 100)}%"
            except ValueError:
                saved_scale = "100%"

        index = self.scale_combo.findText(saved_scale)
        if index >= 0:
            self.scale_combo.setCurrentIndex(index)
        else:
            self.scale_combo.setCurrentIndex(1) # default to 100%

        add_form_row(grid4, "Масштаб интерфейса (под размеры экрана):", self.scale_combo, 0)
        s4_layout.addLayout(grid4)
        layout.addWidget(sect4_card)

        # ----------------------------------------------------
        # СЕКЦИЯ 5: Обновление системы
        # ----------------------------------------------------
        sect5_card = QFrame()
        sect5_card.setProperty("class", "card")
        s5_layout = QVBoxLayout(sect5_card)
        s5_layout.setContentsMargins(20, 20, 20, 20)
        s5_layout.setSpacing(14)

        s5_title = QLabel("Обновление системы (GitHub)")
        s5_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #292524;")
        s5_layout.addWidget(s5_title)

        upd_info_lay = QHBoxLayout()
        from shared.version import VERSION
        self.ver_label = QLabel(f"Текущая версия: <b>{VERSION}</b>")
        self.ver_label.setStyleSheet("font-size: 13px; color: #57534e;")
        upd_info_lay.addWidget(self.ver_label)

        self.upd_status_label = QLabel("")
        self.upd_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #15803d;")
        upd_info_lay.addWidget(self.upd_status_label)
        upd_info_lay.addStretch()
        s5_layout.addLayout(upd_info_lay)

        upd_btn_lay = QHBoxLayout()

        check_upd_btn = QPushButton("Проверить обновления")
        check_upd_btn.setProperty("class", "secondaryBtn")
        check_upd_btn.setCursor(Qt.PointingHandCursor)
        check_upd_btn.clicked.connect(self._check_updates)
        upd_btn_lay.addWidget(check_upd_btn)

        self.download_upd_btn = QPushButton("Скачать обновления")
        self.download_upd_btn.setProperty("class", "primaryBtn")
        self.download_upd_btn.setCursor(Qt.PointingHandCursor)
        self.download_upd_btn.setEnabled(False)
        self.download_upd_btn.clicked.connect(self._download_updates)
        upd_btn_lay.addWidget(self.download_upd_btn)

        self.update_clients_btn = QPushButton("Обновить клиентов")
        self.update_clients_btn.setProperty("class", "secondaryBtn")
        self.update_clients_btn.setCursor(Qt.PointingHandCursor)
        self.update_clients_btn.setEnabled(False)
        self.update_clients_btn.clicked.connect(self._download_updates)
        upd_btn_lay.addWidget(self.update_clients_btn)

        show_clients_btn = QPushButton("Подключенные клиенты")
        show_clients_btn.setProperty("class", "secondaryBtn")
        show_clients_btn.setCursor(Qt.PointingHandCursor)
        show_clients_btn.clicked.connect(self._show_connected_clients)
        upd_btn_lay.addWidget(show_clients_btn)

        upd_btn_lay.addStretch()
        s5_layout.addLayout(upd_btn_lay)

        layout.addWidget(sect5_card)

        # Кнопки действий
        btn_layout = QHBoxLayout()

        save_btn = QPushButton("Сохранить настройки")
        save_btn.setProperty("class", "primaryBtn")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        reset_btn = QPushButton("Сбросить по умолчанию")
        reset_btn.setProperty("class", "secondaryBtn")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(reset_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.stacked_widget.addWidget(self.settings_page)

    def _browse_tests_dir(self):
        try:
            from .storage import set_custom_tests_dir
            from .ui_dialogs import DirectoryChooserDialog
        except ImportError:
            from storage import set_custom_tests_dir
            from ui_dialogs import DirectoryChooserDialog

        current = self.tests_dir_input.text()
        dlg = DirectoryChooserDialog(current, self)
        if dlg.exec():
            chosen = dlg.selected_path
            if chosen and os.path.isdir(chosen):
                self.tests_dir_input.setText(chosen)
                set_custom_tests_dir(chosen)
                if hasattr(self, "_update_dashboard_stats"):
                    self._update_dashboard_stats()
                if hasattr(self, "_update_exams_page_test_view"):
                    self._update_exams_page_test_view()
                if hasattr(self, "show_toast"):
                    self.show_toast(f"Папка с тестами обновлена: {chosen}", "success")

    def _open_current_tests_dir(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        path = self.tests_dir_input.text()
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            try:
                from .storage import tests_dir
            except ImportError:
                from storage import tests_dir
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(tests_dir())))

    def _reset_tests_dir(self):
        try:
            from .storage import default_tests_dir, set_custom_tests_dir
        except ImportError:
            from storage import default_tests_dir, set_custom_tests_dir
        def_dir = str(default_tests_dir())
        self.tests_dir_input.setText(def_dir)
        set_custom_tests_dir(None)
        if hasattr(self, "_update_dashboard_stats"):
            self._update_dashboard_stats()
        if hasattr(self, "_update_exams_page_test_view"):
            self._update_exams_page_test_view()
        if hasattr(self, "show_toast"):
            self.show_toast("Папка с тестами сброшена к стандартной (tests_repo)", "info")

    def _save_settings(self):
        new_port = self.port_spin.value()
        disable_confirm = self.disable_delete_confirm_cb.isChecked()
        auto_export = self.auto_export_csv_cb.isChecked()
        show_notifications = self.show_notifications_cb.isChecked()

        def_duration = self.def_duration_spin.value()
        def_q_limit = self.def_q_limit_spin.value()
        def_attempts = self.def_attempts_spin.value()
        def_random_order = self.def_random_order_cb.isChecked()
        def_shuffle_answers = self.def_shuffle_answers_cb.isChecked()
        def_partial = self.def_partial_cb.isChecked()

        g5 = self.g5_spin.value()
        g4 = self.g4_spin.value()
        g3 = self.g3_spin.value()

        # Валидация порогов
        if not (g5 > g4 > g3):
            QMessageBox.warning(self, "Ошибка", "Пороги оценок должны идти по убыванию:\nОтлично > Хорошо > Удовлетворительно!")
            return

        self.exam_server.DEFAULT_PORT = new_port

        self._settings.setValue("tcp_port", new_port)
        self._settings.setValue("disable_delete_confirm", disable_confirm)
        self._settings.setValue("auto_export_xlsx", auto_export)
        self._settings.setValue("auto_export_csv", auto_export)
        self._settings.setValue("show_notifications", show_notifications)

        # Сохранение директории тестов
        new_tests_dir = self.tests_dir_input.text().strip()
        try:
            from .storage import default_tests_dir, set_custom_tests_dir
        except ImportError:
            from storage import default_tests_dir, set_custom_tests_dir

        if new_tests_dir == str(default_tests_dir()):
            set_custom_tests_dir(None)
        else:
            set_custom_tests_dir(new_tests_dir)

        self._settings.setValue("default_duration", def_duration)
        self._settings.setValue("default_questions_limit", def_q_limit)
        self._settings.setValue("default_attempts", def_attempts)
        self._settings.setValue("default_random_order", def_random_order)
        self._settings.setValue("default_shuffle_answers", def_shuffle_answers)
        self._settings.setValue("default_partial_multiple", def_partial)

        self._settings.setValue("grade_5_min", g5)
        self._settings.setValue("grade_4_min", g4)
        self._settings.setValue("grade_3_min", g3)

        # Сохранение масштабирования
        selected_scale = self.scale_combo.currentText()
        self._settings.setValue("ui_scale", selected_scale)

        self._settings.sync()

        # Обновляем таблицу тестов в репозитории и список тестов в экзаменах
        if hasattr(self, "_update_dashboard_stats"):
            self._update_dashboard_stats()
        if hasattr(self, "_update_exams_page_test_view"):
            self._update_exams_page_test_view()

        # Применяем новые параметры сразу к форме запуска тестов
        if hasattr(self, "_duration_spin"):
            self._duration_spin.setValue(def_duration)
        if hasattr(self, "_questions_limit_spin"):
            self._questions_limit_spin.setValue(def_q_limit)
        if hasattr(self, "_attempts_limit_spin"):
            self._attempts_limit_spin.setValue(def_attempts)
        if hasattr(self, "_random_order_cb"):
            self._random_order_cb.setChecked(def_random_order)
        if hasattr(self, "_shuffle_answers_cb"):
            self._shuffle_answers_cb.setChecked(def_shuffle_answers)
        if hasattr(self, "_partial_multiple_cb"):
            self._partial_multiple_cb.setChecked(def_partial)

        # Мгновенно применяем новый масштаб
        if hasattr(self, "apply_app_scaling"):
            self.apply_app_scaling()

        self.show_toast("Все настройки успешно сохранены!", "success")

    def _reset_settings(self):
        reply = QMessageBox.question(
            self, "Сброс настроек",
            "Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.port_spin.setValue(9876)
            self.disable_delete_confirm_cb.setChecked(False)
            self.auto_export_csv_cb.setChecked(True)
            self.show_notifications_cb.setChecked(True)
            self._reset_tests_dir()
            self.def_duration_spin.setValue(60)
            self.def_q_limit_spin.setValue(10)
            self.def_attempts_spin.setValue(1)
            self.def_random_order_cb.setChecked(False)
            self.def_shuffle_answers_cb.setChecked(False)
            self.def_partial_cb.setChecked(True)
            self.g5_spin.setValue(90)
            self.g4_spin.setValue(70)
            self.g3_spin.setValue(50)
            self.scale_combo.setCurrentIndex(1) # 100%
            self._save_settings()

    def _check_updates(self):
        self.upd_status_label.setText("Проверка...")
        self.upd_status_label.setStyleSheet("font-size: 13px; color: #57534e;")
        self.download_upd_btn.setEnabled(False)

        import threading
        def run_check():
            self.exam_server.log_message.emit("Запущена проверка обновлений на GitHub...")
            update_data, error = self.exam_server.check_for_updates()
            self.update_checked_signal.emit(update_data, error or "")

        threading.Thread(target=run_check, daemon=True).start()

    @Slot(object, str)
    def _on_update_checked(self, update_data, error):
        if update_data:
            self._latest_update_data = update_data

        if not error:
            tag = update_data.get("tag_name", "Неизвестно")
            self.upd_status_label.setText(f"Доступна версия: {tag}")
            self.upd_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #2563eb;")
            self.download_upd_btn.setEnabled(True)
            self.update_clients_btn.setEnabled(True)
        elif error == "latest":
            self.upd_status_label.setText("У вас актуальная версия.")
            self.upd_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #15803d;")
            self.download_upd_btn.setEnabled(False)
            self.update_clients_btn.setEnabled(True)
        else:
            self.upd_status_label.setText(f"Ошибка: {error or 'неизвестно'}")
            self.upd_status_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #dc2626;")
            self.download_upd_btn.setEnabled(False)
            self.update_clients_btn.setEnabled(False)

    def _show_connected_clients(self):
        try:
            from .ui_dialogs import ConnectedClientsDialog
        except ImportError:
            from ui_dialogs import ConnectedClientsDialog
        dlg = ConnectedClientsDialog(self.exam_server, self)
        dlg.exec()

    def _download_updates(self):
        if not hasattr(self, "_latest_update_data"):
            return

        assets = self._latest_update_data.get("assets", [])
        if not assets:
            QMessageBox.warning(self, "Ошибка", "В релизе не найдены файлы для скачивания.")
            return

        # Открываем диалог прогресса
        try:
            from .ui_dialogs import UpdateProgressDialog
        except ImportError:
            from ui_dialogs import UpdateProgressDialog

        self._upd_dialog = UpdateProgressDialog(self.exam_server, self)
        self._upd_dialog.show()

        self.upd_status_label.setText("Запущено обновление...")

        import threading
        def run_download_and_broadcast():
            self.exam_server.log_message.emit("Начато скачивание обновлений сервера и клиентов...")
            upd_dir = self.exam_server.get_updates_dir()
            success_count = 0

            # Автоматически фильтруем нужные файлы на основе ОС сервера и клиентов
            import platform
            server_os = platform.system().lower()

            connected_oses = set()
            for s in self.exam_server._students.values():
                if hasattr(s, 'os') and s.os:
                    connected_oses.add(s.os.lower())

            filtered_assets = []
            for asset in assets:
                name = asset.get("name", "").lower()
                is_server = 'server' in name
                is_student = 'student' in name or 'client' in name
                is_windows = name.endswith('.exe')
                is_linux = not is_windows

                if is_server:
                    if server_os == 'windows' and not is_windows:
                        continue
                    if server_os == 'linux' and not is_linux:
                        continue

                if is_student:
                    if connected_oses:
                        if 'windows' in connected_oses and not is_windows:
                            if 'linux' not in connected_oses:
                                continue
                        if 'linux' in connected_oses and not is_linux:
                            if 'windows' not in connected_oses:
                                continue

                filtered_assets.append(asset)

            # Шаг 1: Скачивание файлов сервера и клиента с GitHub
            total_assets = len(filtered_assets)
            if total_assets == 0:
                self.server_download_progress_signal.emit(100, "Нет подходящих файлов для скачивания.")

            for idx, asset in enumerate(filtered_assets):
                name = asset.get("name", "")
                url = asset.get("browser_download_url", "")
                if name and url:
                    dest = os.path.join(upd_dir, name)
                    self.server_download_progress_signal.emit(
                        int((idx / total_assets) * 100),
                        f"Скачивание: {name}..."
                    )

                    # Передаем progress_callback в download_asset
                    def prog_cb(pct, down, tot):
                        mb_down = down / (1024 * 1024)
                        mb_tot = tot / (1024 * 1024)
                        self.server_download_progress_signal.emit(
                            int(((idx + pct/100) / total_assets) * 100),
                            f"Скачивание {name}: {pct}% ({mb_down:.1f}MB / {mb_tot:.1f}MB)"
                        )

                    if self.exam_server.download_asset(url, dest, prog_cb):
                        success_count += 1

            self.server_download_progress_signal.emit(100, "Все обновления успешно загружены на сервер!")
            self.exam_server.log_message.emit("Обновления успешно скачаны на сервер. Подготовка к раздаче клиентам...")

            # Шаг 2: Если есть подключенные клиенты, передаем обновления им
            students = list(self.exam_server._students.items())
            if students:
                from main import _version_tuple

                # Находим файлы обновлений для каждой ОС
                update_files = {}
                if os.path.exists(upd_dir):
                    for f in os.listdir(upd_dir):
                        path = os.path.join(upd_dir, f)
                        if f.lower().endswith('.exe'):
                            update_files['windows'] = path
                        elif 'student' in f.lower():
                            update_files['linux'] = path

                version_tag = self._latest_update_data.get("tag_name", "").lstrip("v")

                for sock, student in students:
                    client_os = getattr(student, 'os', 'windows')
                    upd_file = update_files.get(client_os)

                    if not upd_file or not os.path.exists(upd_file):
                        self.client_update_progress_signal.emit(sock, 100, "Нет пакета для ОС клиента.")
                        continue

                    client_ver = _version_tuple(getattr(student, 'version', '0.0.0'))

                    # Замыкание ради сохранения sock — сигнал кладёт его в очередь UI.
                    def _make_cb(target_sock):
                        return lambda pct, text: self.client_update_progress_signal.emit(target_sock, pct, text)

                    try:
                        self.exam_server.send_update_to_socket(
                            sock=sock,
                            upd_file=upd_file,
                            name=getattr(student, 'name', '?'),
                            client_os=client_os,
                            version_tag=version_tag,
                            client_version=client_ver,
                            progress_cb=_make_cb(sock),
                            apply_immediately=False,
                        )
                    except Exception as e:
                        self.client_update_progress_signal.emit(sock, 100, f"Ошибка: {e}")
                        self.exam_server.log_message.emit(
                            f"Ошибка при передаче обновления клиенту: {e}"
                        )

            # Включаем кнопку обновления на сервере
            self.exam_server.log_message.emit("Рассылка обновлений всем подключенным клиентам завершена.")
            self.all_updates_ready_signal.emit()

        threading.Thread(target=run_download_and_broadcast, daemon=True).start()

    @Slot(int)
    def _on_update_downloaded(self, success_count):
        pass

    @Slot(int, str)
    def _on_server_download_progress(self, percent, text):
        if hasattr(self, "_upd_dialog") and self._upd_dialog.isVisible():
            self._upd_dialog.set_server_progress(percent, text)

    @Slot(object, int, str)
    def _on_client_update_progress(self, socket, percent, text):
        if hasattr(self, "_upd_dialog") and self._upd_dialog.isVisible():
            self._upd_dialog.set_client_progress(socket, percent, text)

    @Slot()
    def _on_all_updates_ready(self):
        if hasattr(self, "_upd_dialog") and self._upd_dialog.isVisible():
            self._upd_dialog.enable_upgrade()

