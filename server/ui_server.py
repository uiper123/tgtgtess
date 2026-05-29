"""
server/ui_server.py — Графический интерфейс преподавателя (PySide6).
Полностью рабочий Web-dashboard с вкладочной навигацией и мониторингом.
Иконки удалены, используются только понятные надписи.
"""

import os
from datetime import datetime

from PySide6.QtCore import QSettings, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from shared.styles import get_scaled_qss
from shared.version import VERSION

try:
    from .styles import GLOBAL_QSS
    from .ui_dashboard import DashboardMixin
    from .ui_dialogs import (
        DropZoneWidget,
        EditQuestionDialog,
        MonitoringDialog,
        SelectTestFromRepoDialog,
        StudentAnswersDialog,
    )
    from .ui_exams import ExamsMixin
    from .ui_logs import LogsMixin
    from .ui_questions import QuestionsMixin
    from .ui_results import ResultsMixin
    from .ui_settings import SettingsMixin
    from .ui_toasts import ToastNotification
except ImportError:
    from styles import GLOBAL_QSS
    from ui_dashboard import DashboardMixin
    from ui_exams import ExamsMixin
    from ui_logs import LogsMixin
    from ui_questions import QuestionsMixin
    from ui_results import ResultsMixin
    from ui_settings import SettingsMixin
    from ui_toasts import ToastNotification

# ---------------------------------------------------------------------------
# Главное окно Преподавателя
# ---------------------------------------------------------------------------
class ServerWindow(DashboardMixin, QuestionsMixin, ExamsMixin, ResultsMixin, LogsMixin, SettingsMixin, QMainWindow):
    update_checked_signal = Signal(object, str)
    update_downloaded_signal = Signal(int)
    server_download_progress_signal = Signal(int, str)
    client_update_progress_signal = Signal(object, int, str)
    all_updates_ready_signal = Signal()

    def __init__(self, exam_server, parent=None):
        super().__init__(parent)
        self.exam_server = exam_server
        self._settings = QSettings("EduTest", "Server")
        self.setWindowTitle(f"TTGTiSO-Test — Панель преподавателя v{VERSION}")

        self.update_checked_signal.connect(self._on_update_checked)
        self.update_downloaded_signal.connect(self._on_update_downloaded)
        self.server_download_progress_signal.connect(self._on_server_download_progress)
        self.client_update_progress_signal.connect(self._on_client_update_progress)
        self.all_updates_ready_signal.connect(self._on_all_updates_ready)

        # Установка иконки приложения
        from PySide6.QtGui import QIcon
        try:
            from .main import get_resource_path
        except ImportError:
            from main import get_resource_path

        icon_path = get_resource_path("image.ico")
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

    def show_toast(self, message: str, type: str = "success", duration: int = 3000):
        """Отображает всплывающее уведомление, если они включены в настройках."""
        if self._settings.value("show_notifications", True, type=bool):
            toast = ToastNotification(self, message, type, duration)
            toast.show_animation()

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
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        sb_layout = QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)

        # Логотип и кнопка сворачивания
        logo_container = QWidget()
        logo_container.setObjectName("logoContainer")
        logo_container.setStyleSheet("background: transparent; border: none;")
        logo_lay = QHBoxLayout(logo_container)
        logo_lay.setContentsMargins(20, 24, 0, 4)
        logo_lay.setSpacing(10)

        logo = QLabel("TTGTiSO-Test")
        logo.setObjectName("logoLabel")
        logo.setStyleSheet("padding: 0; margin: 0; font-size: 20px; font-weight: 800; color: #ffffff;")
        logo_lay.addWidget(logo)

        logo_lay.addStretch()

        self.collapse_sidebar_btn = QPushButton("◀")
        self.collapse_sidebar_btn.setObjectName("collapseSidebarBtn")
        self.collapse_sidebar_btn.setCursor(Qt.PointingHandCursor)
        self.collapse_sidebar_btn.setFixedSize(28, 28)
        self.collapse_sidebar_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: rgba(255, 255, 255, 0.04);"
            "  color: #a8a29e;"
            "  border: none;"
            "  border-radius: 6px;"
            "  font-size: 11px;"
            "  margin-right: 14px;"
            "}"
            "QPushButton:hover {"
            "  background-color: rgba(255, 255, 255, 0.10);"
            "  color: #fafaf9;"
            "}"
        )
        self.collapse_sidebar_btn.clicked.connect(self.toggle_sidebar)
        logo_lay.addWidget(self.collapse_sidebar_btn)
        sb_layout.addWidget(logo_container)

        sub = QLabel("")
        sub.setObjectName("logoSub")
        sb_layout.addWidget(sub)

        # Индикатор выбранного теста в сайдбаре
        self.selected_test_sidebar_lbl = QLabel("Тест: Новый тест")
        self.selected_test_sidebar_lbl.setObjectName("sidebarSelectedTest")
        self.selected_test_sidebar_lbl.setStyleSheet(
            "QLabel {"
            "  color: #d6d3d1;"
            "  font-size: 11.5px;"
            "  font-weight: 500;"
            "  margin: 2px 14px 14px 14px;"
            "  padding: 8px 12px;"
            "  background-color: rgba(255, 255, 255, 0.04);"
            "  border-radius: 6px;"
            "  border: 1px solid rgba(255, 255, 255, 0.06);"
            "}"
        )
        sb_layout.addWidget(self.selected_test_sidebar_lbl)

        sb_layout.addSpacing(10)

        # Кнопки навигации (Без иконок)
        self.nav_buttons = {}
        nav_items = [
            ("dashboard", "Все тесты"),
            ("exams", "Активные тестирования"),
            ("results", "Результаты студентов"),
            ("logs", "Логи системы"),
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

        # Плашка версии — чтобы преподаватель сразу видел,
        # какая сборка запущена (важно при поддержке/обновлении).
        version_lbl = QLabel(f"TTGTiSO-Test · v{VERSION}")
        version_lbl.setAlignment(Qt.AlignCenter)
        version_lbl.setStyleSheet(
            "background-color: transparent; color: #78716c; font-size: 10.5px; padding: 10px 12px; border-top: 1px solid #292524;"
        )
        sb_layout.addWidget(version_lbl)

        root_layout.addWidget(self.sidebar)

        # --- Главная зона ---
        self.main_container = QWidget()
        main_cont_layout = QVBoxLayout(self.main_container)
        main_cont_layout.setContentsMargins(0, 0, 0, 0)
        main_cont_layout.setSpacing(0)

        # Верхняя панель (видима только когда сайдбар свернут)
        self.top_bar = QWidget()
        self.top_bar.setObjectName("topBar")
        self.top_bar.setStyleSheet(
            "QWidget#topBar {"
            "  background-color: #ffffff;"
            "  border-bottom: 1px solid #e7e5e4;"
            "}"
        )
        self.top_bar.setFixedHeight(50)

        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(16, 0, 16, 0)
        top_bar_layout.setSpacing(12)

        self.expand_sidebar_btn = QPushButton("☰")
        self.expand_sidebar_btn.setObjectName("expandSidebarBtn")
        self.expand_sidebar_btn.setCursor(Qt.PointingHandCursor)
        self.expand_sidebar_btn.setFixedSize(34, 34)
        self.expand_sidebar_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: #ffffff;"
            "  color: #1c1917;"
            "  border: 1px solid #e7e5e4;"
            "  border-radius: 8px;"
            "  font-size: 14px;"
            "  font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "  background-color: #fafaf9;"
            "  border-color: #d6d3d1;"
            "}"
        )
        self.expand_sidebar_btn.clicked.connect(self.toggle_sidebar)
        top_bar_layout.addWidget(self.expand_sidebar_btn)

        self.top_bar_title = QLabel("TTGTiSO-Test — Панель управления")
        self.top_bar_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #1c1917; border: none; background: transparent;")
        top_bar_layout.addWidget(self.top_bar_title)

        top_bar_layout.addStretch()

        main_cont_layout.addWidget(self.top_bar)
        self.top_bar.hide() # Скрыто по умолчанию

        self.stacked_widget = QStackedWidget()
        main_cont_layout.addWidget(self.stacked_widget, 1)

        root_layout.addWidget(self.main_container, 1)

        self._build_dashboard_page()
        self._build_questions_page()
        self._build_exams_page()
        self._build_results_page()
        self._build_logs_page()
        self._build_settings_page()

        # Активная страница по умолчанию
        self.switch_page("exams")

    def toggle_sidebar(self):
        """Сворачивание / разворачивание боковой панели."""
        if self.sidebar.isVisible():
            self.sidebar.hide()
            self.top_bar.show()
        else:
            self.sidebar.show()
            self.top_bar.hide()

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
        elif code == "logs":
            self.stacked_widget.setCurrentWidget(self.logs_page)
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

        # Determine colour + severity bucket from keywords.
        color = "#44403c"  # default
        msg_lower = msg.lower()
        severity = "info"
        if any(w in msg_lower for w in ["ошибка", "error", "отклонён", "отключился", "отменено", "не найден"]):
            color = "#dc2626"
            severity = "error"
        elif any(w in msg_lower for w in ["успешно", "завершен", "подключился", "success", "сохранен"]):
            color = "#16a34a"
            severity = "success"
        elif any(w in msg_lower for w in ["внимание", "пропущено", "предупреждение", "не активен", "ожидание"]):
            color = "#d97706"
            severity = "warning"
        elif any(w in msg_lower for w in ["скачивание", "передача", "загрузка", "обновления"]):
            color = "#2563eb"
            severity = "network"

        formatted_msg = (
            f'<span style="color: #a8a29e;">[{ts}]</span> '
            f'<strong style="color: {color};">{msg}</strong>'
        )

        # Push to persistent buffer so filter toggles can re-render.
        if not hasattr(self, "_log_entries"):
            self._log_entries = []
        self._log_entries.append({
            "ts": ts,
            "text": msg,
            "severity": severity,
            "html": formatted_msg,
        })

        # Honour the active filter — only append to the visible area when
        # the entry matches. If filters aren't built yet, just append.
        show = True
        if hasattr(self, "_log_search") and hasattr(self, "_log_severity"):
            query = self._log_search.text().strip().lower()
            if query and query not in msg_lower:
                show = False
            else:
                wanted = self._severity_for_filter_index(self._log_severity.currentIndex())
                if wanted and wanted != severity:
                    show = False
        if show:
            self._log.append(formatted_msg)

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

        base_min_w = 980
        base_min_h = 640
        base_w = 1300
        base_h = 850

        self.setMinimumSize(int(base_min_w * scale_factor), int(base_min_h * scale_factor))
        self.resize(int(base_w * scale_factor), int(base_h * scale_factor))

        from shared.styles import inject_icon_paths
        scaled_qss = inject_icon_paths(get_scaled_qss(GLOBAL_QSS, scale_factor))
        self.setStyleSheet(scaled_qss)

        if hasattr(self, "_exam_table"):
            self._exam_table.verticalHeader().setDefaultSectionSize(int(54 * scale_factor))
            self._exam_table.setColumnWidth(0, int(300 * scale_factor))
            self._exam_table.setColumnWidth(1, int(120 * scale_factor))
            self._exam_table.setColumnWidth(2, int(120 * scale_factor))
            self._exam_table.setColumnWidth(3, int(120 * scale_factor))
            self._exam_table.setColumnWidth(4, int(240 * scale_factor))

        if hasattr(self, "tests_table"):
            self.tests_table.setColumnWidth(0, int(450 * scale_factor))
            self.tests_table.setColumnWidth(1, int(230 * scale_factor))
            self.tests_table.setColumnWidth(2, int(150 * scale_factor))

        if hasattr(self, "q_table"):
            self.q_table.setColumnWidth(0, int(80 * scale_factor))
            self.q_table.setColumnWidth(1, int(400 * scale_factor))
            self.q_table.setColumnWidth(2, int(120 * scale_factor))
            self.q_table.setColumnWidth(3, int(400 * scale_factor))

        if hasattr(self, "r_table"):
            self.r_table.setColumnWidth(0, int(300 * scale_factor))
            self.r_table.setColumnWidth(1, int(120 * scale_factor))
            self.r_table.setColumnWidth(2, int(190 * scale_factor))
            self.r_table.setColumnWidth(3, int(190 * scale_factor))
            self.r_table.setColumnWidth(4, int(110 * scale_factor))
