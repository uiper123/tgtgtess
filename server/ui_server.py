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

try:
    from .styles import GLOBAL_QSS, get_scaled_qss
    from .ui_dialogs import (
        StudentAnswersDialog, EditQuestionDialog, MonitoringDialog,
        DropZoneWidget, SelectTestFromRepoDialog
    )
    from .ui_dashboard import DashboardMixin
    from .ui_questions import QuestionsMixin
    from .ui_exams import ExamsMixin
    from .ui_results import ResultsMixin
    from .ui_settings import SettingsMixin
except ImportError:
    from styles import GLOBAL_QSS, get_scaled_qss
    from ui_dialogs import (
        StudentAnswersDialog, EditQuestionDialog, MonitoringDialog,
        DropZoneWidget, SelectTestFromRepoDialog
    )
    from ui_dashboard import DashboardMixin
    from ui_questions import QuestionsMixin
    from ui_exams import ExamsMixin
    from ui_results import ResultsMixin
    from ui_settings import SettingsMixin

# ---------------------------------------------------------------------------
# Главное окно Преподавателя
# ---------------------------------------------------------------------------
class ServerWindow(DashboardMixin, QuestionsMixin, ExamsMixin, ResultsMixin, SettingsMixin, QMainWindow):
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

        self.apply_app_scaling()

        self._current_test_group = "Новый тест"

        # Подключение сигналов сервера
        self.exam_server.log_message.connect(self._append_log)
        self.exam_server.server_error.connect(self._show_error)
        self.exam_server.student_connected.connect(self._on_student_connected)
        self.exam_server.student_finished.connect(self._on_student_finished)
        self.exam_server.student_disconnected.connect(self._on_student_disconnected)
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

        sub = QLabel("")
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
    def _on_student_connected(self, name, group):
        self._update_exam_table_view()

    @Slot(str, str, str)
    def _on_student_finished(self, name, group, score):
        self._update_exam_table_view()

    @Slot(str, str)
    def _on_student_disconnected(self, name, group):
        self._update_exam_table_view()

    @Slot(str)
    def _append_log(self, msg: str):
        ts = datetime.now().strftime('%H:%M:%S')
        self._log.append(f"[{ts}] {msg}")

    @Slot(str)
    def _show_error(self, msg: str):
        self._append_log(f"ОШИБКА: {msg}")
        QMessageBox.warning(self, "Ошибка", msg)

    def apply_app_scaling(self):
        saved_scale = self._settings.value("ui_scale", "100%")
        scale_factor = 1.0
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
            
        base_min_w = 1200
        base_min_h = 750
        base_w = 1300
        base_h = 850
        
        self.setMinimumSize(int(base_min_w * scale_factor), int(base_min_h * scale_factor))
        self.resize(int(base_w * scale_factor), int(base_h * scale_factor))
        
        scaled_qss = get_scaled_qss(GLOBAL_QSS, scale_factor)
        self.setStyleSheet(scaled_qss)
        
        if hasattr(self, "_exam_table"):
            self._exam_table.verticalHeader().setDefaultSectionSize(int(54 * scale_factor))
