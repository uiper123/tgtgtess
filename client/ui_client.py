"""
client/ui_client.py — Графический интерфейс студента (PySide6).
Авторизация → Kiosk Mode → Прохождение теста → Завершение.
"""

import sys
import os
import base64
from PySide6.QtCore import Qt, QTimer, Slot, QByteArray, QSettings
from PySide6.QtGui import QPixmap, QFont, QKeyEvent, QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QRadioButton, QCheckBox, QButtonGroup,
    QStackedWidget, QFrame, QProgressBar, QMessageBox,
    QSizePolicy, QScrollArea, QSpacerItem, QComboBox
)
from shared.parser import get_grade_details

try:
    from .styles import CLIENT_QSS
except ImportError:
    from styles import CLIENT_QSS

class StudentWindow(QMainWindow):
    """Главное окно студента: авторизация → тест → результат."""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.setWindowTitle("TTGTiSO-Test — Тестирование")
        
        # Установка иконки приложения
        from PySide6.QtGui import QIcon
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "image.ico"))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setMinimumSize(800, 600)
        self.resize(900, 650)
        self.setStyleSheet(CLIENT_QSS)
        self._settings = QSettings("EduTest", "StudentClient")
        self._login_geometry = None
        self._login_window_flags = self.windowFlags()

        self._questions = []
        self._current_q = 0
        self._answers = {}       # {номер_вопроса: [выбранные_ответы]}
        self._duration = 60
        self._remaining = 0
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._test_finished = False
        self._kiosk_active = False
        self._protection_enabled = False

        # Connect signals
        self.client.connected_ok.connect(self._on_connected_ok)
        self.client.connection_error.connect(self._on_connection_error)
        self.client.result_sent.connect(self._on_result_sent)
        self.client.active_group_found.connect(self._on_active_group_found)
        self.client.force_stopped.connect(self._on_force_stopped)

        self._ip_debounce_timer = QTimer(self)
        self._ip_debounce_timer.setSingleShot(True)
        self._ip_debounce_timer.setInterval(800)
        self._ip_debounce_timer.timeout.connect(self._on_ip_debounce_timeout)

        self._build_ui()
        self._restore_saved_ip()
        QTimer.singleShot(0, self._capture_login_window_state)

    def _capture_login_window_state(self):
        self._login_geometry = self.geometry()
        self._login_window_flags = self.windowFlags()

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self._stack = QStackedWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        self._build_login_page()
        self._build_test_page()
        self._build_result_page()

        self._stack.setCurrentIndex(0)

    # ========================== LOGIN PAGE ==========================
    def _build_login_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(420)
        cl = QVBoxLayout(card)
        cl.setSpacing(16)
        cl.setContentsMargins(32, 32, 32, 32)

        title = QLabel("TTGTiSO-Test")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1e293b; border: none;")
        cl.addWidget(title)

        sub = QLabel("")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 13px; color: #64748b; border: none;")
        cl.addWidget(sub)

        cl.addSpacing(8)

        lbl1 = QLabel("ФИО студента")
        lbl1.setStyleSheet("font-size: 12px; font-weight: bold; color: #64748b; border: none;")
        cl.addWidget(lbl1)
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Иванов Иван Иванович")
        cl.addWidget(self._name_input)

        lbl2 = QLabel("Группа")
        lbl2.setStyleSheet("font-size: 12px; font-weight: bold; color: #64748b; border: none;")
        cl.addWidget(lbl2)
        self._group_input = QComboBox()
        self._group_input.setEditable(True)
        self._group_input.lineEdit().setPlaceholderText("ИСП-311")
        cl.addWidget(self._group_input)
        self._refresh_groups_btn = QPushButton("Обновить")
        self._refresh_groups_btn.setObjectName("refreshGroupsBtn")
        self._refresh_groups_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_groups_btn.clicked.connect(self._request_active_groups)
        cl.addWidget(self._refresh_groups_btn)

        lbl3 = QLabel("IP-адрес сервера")
        lbl3.setStyleSheet("font-size: 12px; font-weight: bold; color: #64748b; border: none;")
        cl.addWidget(lbl3)
        self._ip_input = QLineEdit()
        self._ip_input.setPlaceholderText("192.168.1.100")
        self._ip_input.textChanged.connect(self._on_ip_text_changed)
        cl.addWidget(self._ip_input)

        cl.addSpacing(8)

        self._connect_btn = QPushButton("Подключиться к экзамену")
        self._connect_btn.setObjectName("connectBtn")
        self._connect_btn.setCursor(Qt.PointingHandCursor)
        self._connect_btn.clicked.connect(self._do_connect)
        cl.addWidget(self._connect_btn)

        self._login_error = QLabel("")
        self._login_error.setAlignment(Qt.AlignCenter)
        self._login_error.setStyleSheet("color: #ef4444; font-size: 12px; border: none;")
        self._login_error.hide()
        cl.addWidget(self._login_error)

        outer.addWidget(card)
        self._stack.addWidget(page)

    # ========================== TEST PAGE ==========================
    def _build_test_page(self):
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        # ----------------------------------------------------
        # Top bar: Left (User Info), Center (Progress), Right (Timer)
        # ----------------------------------------------------
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: #ffffff; border-bottom: 1px solid #e2e8f0;")
        tb_layout = QHBoxLayout(top_bar)
        tb_layout.setContentsMargins(32, 14, 32, 14)
        tb_layout.setSpacing(24)

        # Left: Student Name and Group
        user_info = QWidget()
        ui_layout = QVBoxLayout(user_info)
        ui_layout.setContentsMargins(0, 0, 0, 0)
        ui_layout.setSpacing(2)
        
        self._student_name_label = QLabel("Имя Фамилия")
        self._student_name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #1e293b; border: none;")
        self._student_group_label = QLabel("Группа: ---")
        self._student_group_label.setStyleSheet("font-size: 11px; color: #64748b; border: none;")
        ui_layout.addWidget(self._student_name_label)
        ui_layout.addWidget(self._student_group_label)
        tb_layout.addWidget(user_info)

        # Center: Progress Bar & Question Counter Info
        progress_container = QWidget()
        pc_layout = QVBoxLayout(progress_container)
        pc_layout.setContentsMargins(0, 0, 0, 0)
        pc_layout.setSpacing(4)

        info_layout = QHBoxLayout()
        self._q_counter = QLabel("Вопрос 1 из 1")
        self._q_counter.setStyleSheet("font-size: 12px; font-weight: bold; color: #475569; border: none;")
        self._percent_label = QLabel("0%")
        self._percent_label.setStyleSheet("font-size: 12px; font-weight: bold; color: #64748b; border: none;")
        info_layout.addWidget(self._q_counter)
        info_layout.addStretch()
        info_layout.addWidget(self._percent_label)
        pc_layout.addLayout(info_layout)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFixedHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background-color: #e2e8f0; border: none; border-radius: 4px; }"
            "QProgressBar::chunk { background-color: #10b981; border-radius: 4px; }"
        )
        pc_layout.addWidget(self._progress)
        
        tb_layout.addWidget(progress_container, 1)

        # Right: Timer
        self._timer_label = QLabel("60:00")
        self._timer_label.setObjectName("timerLabel")
        self._timer_label.setStyleSheet(
            "font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 22px; font-weight: bold; color: #ef4444; border: none;"
        )
        tb_layout.addWidget(self._timer_label)

        pl.addWidget(top_bar)

        # ----------------------------------------------------
        # Main Title Section
        # ----------------------------------------------------
        title_section = QWidget()
        title_section.setStyleSheet("background-color: #f8fafc; border: none;")
        ts_layout = QHBoxLayout(title_section)
        ts_layout.setContentsMargins(40, 24, 40, 0)
        
        title_text_layout = QVBoxLayout()
        self._test_title = QLabel("Итоговое тестирование")
        self._test_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #0f172a; border: none;")
        self._test_subtitle = QLabel("Раздел: Основная часть")
        self._test_subtitle.setStyleSheet("font-size: 13px; color: #64748b; border: none;")
        title_text_layout.addWidget(self._test_title)
        title_text_layout.addWidget(self._test_subtitle)
        ts_layout.addLayout(title_text_layout)
        ts_layout.addStretch()

        pl.addWidget(title_section)

        # ----------------------------------------------------
        # Scrollable Question area
        # ----------------------------------------------------
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: #f8fafc;")

        self._q_container = QWidget()
        self._q_container.setStyleSheet("background-color: #f8fafc;")
        self._q_layout = QVBoxLayout(self._q_container)
        self._q_layout.setContentsMargins(40, 16, 40, 16)
        self._q_layout.setSpacing(16)
        self._q_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._q_container)
        pl.addWidget(scroll, 1)

        # ----------------------------------------------------
        # Bottom Navigation Bar
        # ----------------------------------------------------
        bottom = QWidget()
        bottom.setObjectName("bottomBar")
        bottom.setStyleSheet("#bottomBar { background-color: #ffffff; border-top: 1px solid #e2e8f0; }")
        bb = QHBoxLayout(bottom)
        bb.setContentsMargins(40, 16, 40, 16)
        bb.setSpacing(16)

        # Left: Prev question button
        self._prev_btn = QPushButton("Предыдущий вопрос")
        self._prev_btn.setObjectName("prevBtn")
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.clicked.connect(self._prev_question)
        self._prev_btn.setProperty("class", "secondaryBtn")
        bb.addWidget(self._prev_btn)

        bb.addStretch()

        # Center: Progress saving indicator
        self._saving_status = QLabel("")
        self._saving_status.setStyleSheet("font-size: 12px; color: #94a3b8; border: none;")
        bb.addWidget(self._saving_status)

        bb.addStretch()

        # Right: Next / Finish button
        self._next_btn = QPushButton("Ответить и продолжить")
        self._next_btn.setObjectName("nextBtn")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.clicked.connect(self._next_question)
        bb.addWidget(self._next_btn)

        pl.addWidget(bottom)

        self._stack.addWidget(page)

    # ========================== RESULT PAGE ==========================
    def _build_result_page(self):
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setMinimumWidth(550)
        card.setMaximumWidth(700)
        cl = QVBoxLayout(card)
        cl.setSpacing(12)
        cl.setContentsMargins(32, 40, 32, 40)
        cl.setAlignment(Qt.AlignCenter)

        icon = QLabel("Успешно")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 24px; color: #10b981; font-weight: bold; border: none;")
        cl.addWidget(icon)

        title = QLabel("Тест завершён!")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #1e293b; border: none;")
        cl.addWidget(title)

        self._result_score = QLabel("0/0")
        self._result_score.setAlignment(Qt.AlignCenter)
        self._result_score.setStyleSheet("font-size: 36px; font-weight: bold; color: #3b82f6; border: none;")
        cl.addWidget(self._result_score)

        self._result_grade = QLabel("")
        self._result_grade.setAlignment(Qt.AlignCenter)
        cl.addWidget(self._result_grade)

        self._result_sub = QLabel("Результат отправлен преподавателю")
        self._result_sub.setAlignment(Qt.AlignCenter)
        self._result_sub.setStyleSheet("font-size: 13px; color: #64748b; border: none;")
        cl.addWidget(self._result_sub)

        cl.addSpacing(12)
        
        ok_btn = QPushButton("Вернуться на экран входа")
        ok_btn.setProperty("class", "primaryBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.clicked.connect(self._reset_to_login)
        cl.addWidget(ok_btn)

        outer.addWidget(card)
        self._stack.addWidget(page)

    # ========================== LOGIC ==========================

    def _reset_to_login(self):
        self.client.disconnect()
        self._kiosk_active = False
        self._protection_enabled = False
        self._focus_loss_count = 0
        self.hide()
        self.setWindowFlags(self._login_window_flags)
        self._name_input.clear()
        self._group_input.clear()
        self._name_input.setPlaceholderText("Иванов Иван Иванович")
        self._group_input.lineEdit().setPlaceholderText("ИСП-311")
        self._ip_input.setPlaceholderText("192.168.1.100")
        self._name_input.setEnabled(True)
        self._group_input.setEnabled(True)
        self._group_input.lineEdit().setEnabled(True)
        self._ip_input.setEnabled(True)
        self._name_input.setReadOnly(False)
        self._group_input.lineEdit().setReadOnly(False)
        self._ip_input.setReadOnly(False)
        self._connect_btn.setEnabled(True)
        self._connect_btn.setText("Подключиться к экзамену")
        self._login_error.hide()
        self._stack.setCurrentIndex(0)
        self.showNormal()
        QTimer.singleShot(0, self._restore_login_window_state)
        QTimer.singleShot(120, self._restore_login_window_state)
        self._request_active_groups()

    def _restore_login_window_state(self):
        self.setMinimumSize(800, 600)
        if self._login_geometry is not None:
            self.setGeometry(self._login_geometry)
        else:
            self.resize(900, 650)
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._name_input.setFocus(Qt.OtherFocusReason)

    def _on_ip_text_changed(self):
        self._save_current_ip()
        self._ip_debounce_timer.start()

    def _save_current_ip(self):
        ip = self._ip_input.text().strip()
        if ip:
            self._settings.setValue("last_server_ip", ip)
        else:
            self._settings.remove("last_server_ip")
        self._settings.sync()

    def _on_ip_debounce_timeout(self):
        self._request_active_groups()

    def _request_active_groups(self):
        ip = self._ip_input.text().strip()
        if not ip:
            self._save_current_ip()
            return
        self._save_current_ip()
        port = 9876
        if ':' in ip:
            parts = ip.rsplit(':', 1)
            ip = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass
        self.client.check_active_group(ip, port)

    def _restore_saved_ip(self):
        ip = self._settings.value("last_server_ip", "", str).strip()
        if not ip:
            return
        self._ip_input.setText(ip)
        QTimer.singleShot(0, self._request_active_groups)

    @Slot(list)
    def _on_active_group_found(self, groups: list):
        current = self._group_input.currentText().strip()
        self._group_input.clear()
        clean_groups = []
        for group in groups:
            text = str(group).strip()
            if text and text not in clean_groups:
                clean_groups.append(text)
        self._group_input.addItems(clean_groups)
        if current and current in clean_groups:
            self._group_input.setCurrentText(current)
        elif clean_groups:
            self._group_input.setCurrentIndex(0)
        elif current:
            self._group_input.setEditText(current)
        self._group_input.lineEdit().setPlaceholderText(
            "Выберите активную группу" if clean_groups else "Активных групп нет"
        )

    def _do_connect(self):
        name = self._name_input.text().strip()
        group = self._group_input.currentText().strip()
        ip = self._ip_input.text().strip()

        if not name or not group or not ip:
            if ip and not group:
                self._request_active_groups()
            self._login_error.setText("Заполните все поля!")
            self._login_error.show()
            return

        self._login_error.hide()
        self._connect_btn.setEnabled(False)
        self._connect_btn.setText("Подключение...")

        # Извлекаем порт, если указан
        port = 9876
        if ':' in ip:
            parts = ip.rsplit(':', 1)
            ip = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass

        self.client.connect_to_server(ip, port, name, group)

    @Slot(list, int, str, str)
    def _on_connected_ok(self, questions, duration, title, section):
        self._questions = questions
        self._duration = duration
        self._remaining = duration * 60
        self._current_q = 0
        self._answers.clear()
        self._test_finished = False

        # Установка кастомных заголовков
        self._test_title.setText(title)
        self._test_subtitle.setText(section)

        # Set user details
        self._student_name_label.setText(self._name_input.text())
        self._student_group_label.setText(f"Группа: {self._group_input.currentText()}")

        # Activate kiosk mode
        self._activate_kiosk()

        # Show test page
        self._stack.setCurrentIndex(1)
        self._show_question(0)
        self._timer.start()

    @Slot(str)
    def _on_connection_error(self, msg):
        # Если студент сейчас проходит тест (находится на странице тестирования)
        if self._stack.currentIndex() == 1:
            self._collect_current_answer()
            self._update_saving_status()
            return

        self._connect_btn.setEnabled(True)
        self._connect_btn.setText("Подключиться к экзамену")
        self._login_error.setText(msg)
        self._login_error.show()

    @Slot(str)
    def _on_result_sent(self, score):
        self._result_score.setText(score)
        self._result_sub.setText("Результат отправлен преподавателю")
        grade_text, grade_color = get_grade_details(score)
        self._result_grade.setText(f"Процент прохождения: {grade_text}")
        
        # Convert hex color to rgba for clean background
        hex_color = grade_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        self._result_grade.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {grade_color}; "
            f"background-color: rgba({r}, {g}, {b}, 0.12); padding: 12px 24px; border-radius: 8px; border: none;"
        )

    @Slot()
    def _on_force_stopped(self):
        if self._test_finished:
            return
        self._timer.stop()
        self._test_finished = True
        QMessageBox.warning(
            self, "Тестирование остановлено",
            "Тестирование принудительно остановлено преподавателем.\nВаши текущие ответы не сохранены.",
            QMessageBox.Ok
        )
        self._reset_to_login()

    def _activate_kiosk(self):
        """Включает режим киоска: полноэкранное окно без рамок."""
        self._capture_login_window_state()
        self._kiosk_active = True
        self._protection_enabled = False
        self.setWindowFlags(
            Qt.Window | Qt.CustomizeWindowHint | Qt.WindowStaysOnTopHint
        )
        self.showFullScreen()
        # Включаем прокторинг с задержкой в 1.5 секунды, когда переход на полный экран полностью завершен
        QTimer.singleShot(1500, self._enable_protection)

    def _enable_protection(self):
        if getattr(self, "_kiosk_active", False) and not getattr(self, "_test_finished", False):
            self._protection_enabled = True
            self.activateWindow()

    def _show_question(self, index: int):
        """Отображает вопрос по индексу."""
        # Очистка
        while self._q_layout.count():
            child = self._q_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if index >= len(self._questions):
            return

        q = self._questions[index]
        total = len(self._questions)

        # Counter & progress
        self._q_counter.setText(f"Вопрос {index + 1} из {total}")
        percent = int(((index + 1) / total) * 100) if total > 0 else 0
        self._percent_label.setText(f"{percent}%")
        self._progress.setValue(percent)

        # Question card
        card = QFrame()
        card.setObjectName("questionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(20)

        # Header layout
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)
        header_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Question number badge
        badge = QLabel(str(index + 1))
        badge.setStyleSheet(
            "background-color: #f1f5f9; color: #475569; font-weight: bold; "
            "font-size: 14px; padding: 8px 12px; border-radius: 6px; border: none;"
        )
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(36, 36)
        header_layout.addWidget(badge)

        # Question text
        q_text = QLabel(q.get('text', ''))
        q_text.setWordWrap(True)
        q_text.setProperty("class", "qText")
        q_text.setStyleSheet("font-size: 18px; font-weight: bold; color: #0f172a; border: none;")
        header_layout.addWidget(q_text, 1)

        card_layout.addLayout(header_layout)

        if q.get('written'):
            hint = QLabel("Письменный ответ — введите ваш ответ в поле ниже")
            hint.setStyleSheet("color: #3b82f6; font-size: 13px; font-weight: bold; border: none; margin-left: 52px;")
            card_layout.addWidget(hint)
        elif q.get('multiple'):
            hint = QLabel("Множественный выбор — выберите все правильные варианты")
            hint.setStyleSheet("color: #f59e0b; font-size: 13px; font-weight: bold; border: none; margin-left: 52px;")
            card_layout.addWidget(hint)

        # Image (if present)
        image_data = q.get('image_data')
        if image_data:
            img_label = QLabel()
            img_label.setAlignment(Qt.AlignCenter)
            img_label.setStyleSheet("border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px; margin-left: 52px;")
            try:
                pixmap = QPixmap()
                pixmap.loadFromData(QByteArray(base64.b64decode(image_data, validate=True)))
                if pixmap.isNull():
                    raise ValueError("empty image")
                scaled = pixmap.scaled(600, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label.setPixmap(scaled)
            except (ValueError, base64.binascii.Error):
                img_label.setText("Изображение не удалось загрузить")
            card_layout.addWidget(img_label)

        # Answers
        card_layout.addSpacing(4)
        answers = q.get('answers', [])
        self._answer_widgets = []

        q_num = q.get('number', index + 1)
        previous_answers = self._answers.get(q_num, [])

        if q.get('written'):
            ans_input = QLineEdit()
            ans_input.setPlaceholderText("Введите ваш ответ здесь...")
            if previous_answers:
                ans_input.setText(previous_answers[0])
            ans_input.setStyleSheet(
                "QLineEdit {"
                "  background-color: #ffffff;"
                "  border: 2px solid #cbd5e1;"
                "  border-radius: 10px;"
                "  padding: 12px 16px;"
                "  font-size: 15px;"
                "  color: #0f172a;"
                "  margin-left: 52px;"
                "  min-height: 24px;"
                "}"
                "QLineEdit:focus {"
                "  border-color: #3b82f6;"
                "}"
            )
            ans_input.textChanged.connect(self._on_answer_changed)
            card_layout.addWidget(ans_input)
            self._answer_widgets.append(ans_input)
        elif q.get('multiple'):
            for ans_text in answers:
                cb = QCheckBox(ans_text)
                cb.setCursor(Qt.PointingHandCursor)
                if ans_text in previous_answers:
                    cb.setChecked(True)
                cb.stateChanged.connect(self._on_answer_changed)
                card_layout.addWidget(cb)
                self._answer_widgets.append(cb)
        else:
            self._radio_group = QButtonGroup(card)
            self._radio_group.setExclusive(True)
            for i, ans_text in enumerate(answers):
                rb = QRadioButton(ans_text)
                rb.setCursor(Qt.PointingHandCursor)
                if ans_text in previous_answers:
                    rb.setChecked(True)
                rb.toggled.connect(self._on_answer_changed)
                self._radio_group.addButton(rb, i)
                card_layout.addWidget(rb)
                self._answer_widgets.append(rb)

        self._q_layout.addWidget(card)
        self._q_layout.addStretch()

        # Update Navigation buttons states
        self._prev_btn.setEnabled(index > 0)
        
        is_last = (index == total - 1)
        if is_last:
            self._next_btn.setText("Завершить тест")
            self._next_btn.setObjectName("finishBtn")
            self._next_btn.setProperty("class", "finishBtn")
        else:
            self._next_btn.setText("Ответить и продолжить")
            self._next_btn.setObjectName("nextBtn")
            self._next_btn.setProperty("class", "nextBtn")
        self._next_btn.style().unpolish(self._next_btn)
        self._next_btn.style().polish(self._next_btn)

    def _on_answer_changed(self):
        self._collect_current_answer()

    def _update_saving_status(self):
        from datetime import datetime
        from PySide6.QtNetwork import QAbstractSocket
        now_str = datetime.now().strftime("%H:%M:%S")
        if self.client._socket.state() == QAbstractSocket.ConnectedState:
            self._saving_status.setText(f"✓ Прогресс сохранен в {now_str}")
            self._saving_status.setStyleSheet("font-size: 12px; color: #10b981; font-weight: bold; border: none;")
        else:
            self._saving_status.setText(f"⚠️ Офлайн-режим: прогресс сохранен в {now_str}")
            self._saving_status.setStyleSheet("font-size: 12px; color: #ef4444; font-weight: bold; border: none;")

    def _collect_current_answer(self):
        """Сохраняет ответ на текущий вопрос."""
        if self._current_q >= len(self._questions):
            return
        q = self._questions[self._current_q]
        q_num = q.get('number', self._current_q + 1)
        selected = []
        
        if q.get('written'):
            if self._answer_widgets:
                w = self._answer_widgets[0]
                if isinstance(w, QLineEdit):
                    selected.append(w.text().strip())
        else:
            for w in self._answer_widgets:
                if isinstance(w, (QRadioButton, QCheckBox)) and w.isChecked():
                    selected.append(w.text())
                    
        self._answers[q_num] = selected
        
        # Автосохранение бэкапа локально при любом сохранении ответа!
        self.client.save_backup(self._answers)
        self._update_saving_status()

    def _prev_question(self):
        self._collect_current_answer()
        if self._current_q > 0:
            self._current_q -= 1
            self._show_question(self._current_q)

    def _next_question(self):
        self._collect_current_answer()
        if self._current_q < len(self._questions) - 1:
            self._current_q += 1
            self._show_question(self._current_q)
        else:
            self._finish_test()

    def _finish_test(self):
        self._collect_current_answer()
        self._timer.stop()
        self._test_finished = True

        # Сохраняем итоговый пользовательский бэкап в текущую рабочую директорию
        from client.main import save_student_final_backup
        name = self._name_input.text()
        group = self._group_input.currentText()
        score_placeholder = f"{len(self._answers)}/{len(self._questions)}"
        backup_path = save_student_final_backup(name, group, score_placeholder, self._answers)
        backup_filename = os.path.basename(backup_path) if backup_path else "Бэкап.log"

        sent = self.client.send_result(self._answers)
        if sent:
            self._result_score.setText("Расчёт...")
            self._result_sub.setText(f"Результат отправлен на сервер.\nСоздана локальная резервная копия: резервная копия/{backup_filename}")
        else:
            self._result_score.setText("Не отправлено")
            self._result_grade.setText("")
            self._result_sub.setText(f"Соединение с сервером потеряно.\nЛокальная копия сохранена в: резервная копия/{backup_filename}")

        # Deactivate kiosk
        self._kiosk_active = False
        self._protection_enabled = False
        self.hide()
        self.setWindowFlags(self._login_window_flags)
        self.showNormal()
        if self._login_geometry is not None:
            self.setGeometry(self._login_geometry)
        self._stack.setCurrentIndex(2)

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._finish_test()
            return
        mins = self._remaining // 60
        secs = self._remaining % 60
        self._timer_label.setText(f"{mins:02d}:{secs:02d}")

        # Краснеет при < 2 минут
        if self._remaining < 120:
            self._timer_label.setStyleSheet(
                "font-family: 'Consolas', 'Courier New', monospace; "
                "font-size: 28px; font-weight: bold; color: #ef4444;"
            )

    # ========================== KIOSK PROTECTION ==========================

    def closeEvent(self, event: QCloseEvent):
        if self._kiosk_active and not self._test_finished:
            event.ignore()
        else:
            if not self._test_finished and self._stack.currentIndex() == 1:
                self._collect_current_answer()
            event.accept()

    def keyPressEvent(self, event: QKeyEvent):
        if self._kiosk_active and not self._test_finished:
            key = event.key()
            mods = event.modifiers()
            # Block Escape, Alt+F4, Ctrl+W, Windows key
            if key == Qt.Key_Escape:
                event.ignore()
                return
            if key == Qt.Key_F4 and (mods & Qt.AltModifier):
                event.ignore()
                return
            if key == Qt.Key_W and (mods & Qt.ControlModifier):
                event.ignore()
                return
            if key in (Qt.Key_Super_L, Qt.Key_Super_R, Qt.Key_Meta):
                event.ignore()
                return
        super().keyPressEvent(event)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent
        if event.type() == QEvent.ActivationChange:
            if getattr(self, "_kiosk_active", False) and getattr(self, "_protection_enabled", False) and not getattr(self, "_test_finished", False):
                if self._stack.currentIndex() == 1:
                    if not self.isActiveWindow():
                        self._handle_focus_loss()
        super().changeEvent(event)

    def _handle_focus_loss(self):
        if getattr(self, "_test_finished", False):
            return
            
        self._focus_loss_count = getattr(self, "_focus_loss_count", 0) + 1
        
        # Отправляем предупреждение на сервер
        warning_desc = f"Потеря фокуса / Переключение рабочего стола (Предупреждение {self._focus_loss_count})"
        self.client.send_cheat_warning(warning_desc)
        
        if self._focus_loss_count >= 3:
            self._timer.stop()
            self._test_finished = True
            QMessageBox.critical(
                self, "ТЕСТ БЛОКИРОВАН",
                "Превышено допустимое количество попыток сворачивания окна (3/3)!\n"
                "Ваш тест автоматически завершен с сохранением текущих ответов и заблокирован за нарушение правил.",
                QMessageBox.Ok
            )
            self._finish_test()
        else:
            QMessageBox.warning(
                self, "ВНИМАНИЕ — ПОПЫТКА СПИСАТЬ",
                f"Обнаружен выход из полноэкранного режима или переключение рабочего стола!\n"
                f"Во время тестирования запрещено переключать окна и рабочие столы.\n\n"
                f"Предупреждение {self._focus_loss_count} из 3.\n"
                f"При достижении 3 предупреждений ваш тест будет автоматически заблокирован!",
                QMessageBox.Ok
            )
            # Принудительно возвращаем фокус и разворачиваем обратно
            self.showFullScreen()
            self.activateWindow()
