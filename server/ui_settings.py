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

