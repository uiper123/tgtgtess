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

class SettingsMixin:
    def _build_settings_page(self):
        self.settings_page = QWidget()
        main_layout = QVBoxLayout(self.settings_page)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Создаем QScrollArea для удобной прокрутки настроек
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        title = QLabel("Настройки системы")
        title.setProperty("class", "sectionTitle")
        layout.addWidget(title)

        # Вспомогательный метод для стилизации рядов настроек
        def add_form_row(grid_layout, label_text, widget, row_idx):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-size: 13px; font-weight: 500; color: #475569; background: transparent;")
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
        s1_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e293b;")
        s1_layout.addWidget(s1_title)

        # Порт
        port_lay = QHBoxLayout()
        lbl_port = QLabel("Порт TCP-сервера:")
        lbl_port.setStyleSheet("font-size: 13px; font-weight: 500; color: #475569; background: transparent;")
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
        self.disable_delete_confirm_cb.setObjectName("randomOrderCheck")
        self.disable_delete_confirm_cb.setCursor(Qt.PointingHandCursor)
        self.disable_delete_confirm_cb.setChecked(self._get_disable_delete_confirm())
        s1_layout.addWidget(self.disable_delete_confirm_cb)

        # Автоэкспорт в CSV
        self.auto_export_csv_cb = QCheckBox("Автоматически экспортировать результаты в CSV-файл при остановке экзамена")
        self.auto_export_csv_cb.setObjectName("partialScoreCheck")
        self.auto_export_csv_cb.setCursor(Qt.PointingHandCursor)
        self.auto_export_csv_cb.setChecked(self._settings.value("auto_export_csv", True, type=bool))
        s1_layout.addWidget(self.auto_export_csv_cb)

        layout.addWidget(sect1_card)

        # ----------------------------------------------------
        # СЕКЦИЯ 2: Параметры запуска экзамена по умолчанию
        # ----------------------------------------------------
        sect2_card = QFrame()
        sect2_card.setProperty("class", "card")
        s2_layout = QVBoxLayout(sect2_card)
        s2_layout.setContentsMargins(20, 20, 20, 20)
        s2_layout.setSpacing(14)

        s2_title = QLabel("Параметры запуска экзаменов по умолчанию")
        s2_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e293b;")
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
        self.def_random_order_cb.setObjectName("randomOrderCheck")
        self.def_random_order_cb.setCursor(Qt.PointingHandCursor)
        self.def_random_order_cb.setChecked(self._settings.value("default_random_order", False, type=bool))
        s2_layout.addWidget(self.def_random_order_cb)

        self.def_partial_cb = QCheckBox("Разрешить частичный зачет баллов для множественного выбора по умолчанию")
        self.def_partial_cb.setObjectName("partialScoreCheck")
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
        s3_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #1e293b;")
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

    def _save_settings(self):
        new_port = self.port_spin.value()
        disable_confirm = self.disable_delete_confirm_cb.isChecked()
        auto_export = self.auto_export_csv_cb.isChecked()
        
        def_duration = self.def_duration_spin.value()
        def_q_limit = self.def_q_limit_spin.value()
        def_attempts = self.def_attempts_spin.value()
        def_random_order = self.def_random_order_cb.isChecked()
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
        self._settings.setValue("auto_export_csv", auto_export)
        
        self._settings.setValue("default_duration", def_duration)
        self._settings.setValue("default_questions_limit", def_q_limit)
        self._settings.setValue("default_attempts", def_attempts)
        self._settings.setValue("default_random_order", def_random_order)
        self._settings.setValue("default_partial_multiple", def_partial)

        self._settings.setValue("grade_5_min", g5)
        self._settings.setValue("grade_4_min", g4)
        self._settings.setValue("grade_3_min", g3)
        self._settings.sync()

        # Применяем новые параметры сразу к форме запуска тестов
        if hasattr(self, "_duration_spin"):
            self._duration_spin.setValue(def_duration)
        if hasattr(self, "_questions_limit_spin"):
            self._questions_limit_spin.setValue(def_q_limit)
        if hasattr(self, "_attempts_limit_spin"):
            self._attempts_limit_spin.setValue(def_attempts)
        if hasattr(self, "_random_order_cb"):
            self._random_order_cb.setChecked(def_random_order)
        if hasattr(self, "_partial_multiple_cb"):
            self._partial_multiple_cb.setChecked(def_partial)

        QMessageBox.information(self, "Настройки", "Все настройки успешно сохранены и применены!")

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
            self.def_duration_spin.setValue(60)
            self.def_q_limit_spin.setValue(10)
            self.def_attempts_spin.setValue(1)
            self.def_random_order_cb.setChecked(False)
            self.def_partial_cb.setChecked(True)
            self.g5_spin.setValue(90)
            self.g4_spin.setValue(70)
            self.g3_spin.setValue(50)
            self._save_settings()

