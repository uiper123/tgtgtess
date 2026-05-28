from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer
from PySide6.QtWidgets import QGraphicsOpacityEffect, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class ToastNotification(QWidget):
    def __init__(self, parent, message, type="success", duration=3000):
        super().__init__(parent)
        # Устанавливаем флаги для плавающего окна поверх родителя
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.message = message
        self.type = type
        self.duration = duration

        self._setup_ui()

        # Анимации
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.pos_anim = QPropertyAnimation(self, b"geometry")

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_animation)

    def _setup_ui(self):
        # Основной виджет-контейнер для фона
        container = QWidget(self)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        icon_lbl = QLabel()

        if self.type == "success":
            icon_lbl.setText("✓")
            bg_color = "#ecfdf5"
            border_color = "#10b981"
            text_color = "#065f46"
        elif self.type == "info":
            icon_lbl.setText("ℹ")
            bg_color = "#eff6ff"
            border_color = "#3b82f6"
            text_color = "#1e40af"
        elif self.type == "warning":
            icon_lbl.setText("⚠️")
            bg_color = "#fffbeb"
            border_color = "#f59e0b"
            text_color = "#92400e"
        elif self.type == "error":
            icon_lbl.setText("✕")
            bg_color = "#fef2f2"
            border_color = "#ef4444"
            text_color = "#991b1b"
        else:
            icon_lbl.setText("•")
            bg_color = "#ffffff"
            border_color = "#cbd5e1"
            text_color = "#334155"

        icon_lbl.setStyleSheet(f"color: {text_color}; font-size: 16px; font-weight: bold; background: transparent;")
        layout.addWidget(icon_lbl)

        text_lbl = QLabel(self.message)
        text_lbl.setStyleSheet(f"color: {text_color}; font-size: 13px; font-weight: bold; background: transparent;")
        layout.addWidget(text_lbl)

        container.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        self.adjustSize()

    def show_animation(self):
        if not self.parentWidget():
            return

        # Определяем глобальные координаты родителя
        parent_pos = self.parentWidget().mapToGlobal(self.parentWidget().rect().topLeft())
        parent_w = self.parentWidget().width()
        parent_h = self.parentWidget().height()

        # Позиция: снизу по центру
        start_x = parent_pos.x() + (parent_w - self.width()) // 2
        end_y = parent_pos.y() + parent_h - self.height() - 30
        start_y = end_y + 20

        self.setGeometry(start_x, start_y, self.width(), self.height())

        self.opacity_anim.setDuration(200)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)

        self.pos_anim.setDuration(300)
        self.pos_anim.setStartValue(QRect(start_x, start_y, self.width(), self.height()))
        self.pos_anim.setEndValue(QRect(start_x, end_y, self.width(), self.height()))
        self.pos_anim.setEasingCurve(QEasingCurve.OutQuad)

        self.show()
        self.opacity_anim.start()
        self.pos_anim.start()

        self._timer.start(self.duration)

    def hide_animation(self):
        self.opacity_anim.setDuration(200)
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)

        self.pos_anim.setDuration(200)
        cur_geom = self.geometry()
        self.pos_anim.setStartValue(cur_geom)
        self.pos_anim.setEndValue(QRect(cur_geom.x(), cur_geom.y() + 10, cur_geom.width(), cur_geom.height()))

        self.opacity_anim.finished.connect(self.deleteLater)
        self.opacity_anim.start()
        self.pos_anim.start()
