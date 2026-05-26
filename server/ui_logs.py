import os
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFrame
)

class LogsMixin:
    def _build_logs_page(self):
        self.logs_page = QWidget()
        main_layout = QVBoxLayout(self.logs_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Главный контейнер
        content = QWidget()
        content.setObjectName("logsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Заголовок и кнопки
        header_layout = QHBoxLayout()
        title = QLabel("Логи системы")
        title.setProperty("class", "sectionTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        clear_btn = QPushButton("Очистить логи")
        clear_btn.setProperty("class", "secondaryBtn")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_logs)
        header_layout.addWidget(clear_btn)

        layout.addLayout(header_layout)

        subtitle = QLabel("Подробный журнал работы сервера и подключений студентов")
        subtitle.setProperty("class", "sectionSub")
        layout.addWidget(subtitle)

        # Зона с текстом логов
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._log = QTextEdit()
        self._log.setObjectName("logArea")
        self._log.setReadOnly(True)
        self._log.setStyleSheet("border: none; padding: 12px; font-family: 'Consolas', 'Courier New', monospace; font-size: 13px; color: #334155;")
        card_layout.addWidget(self._log)

        layout.addWidget(card, 1)

        main_layout.addWidget(content)
        self.stacked_widget.addWidget(self.logs_page)

    def _clear_logs(self):
        self._log.clear()
        self.exam_server.log_message.emit("Логи очищены")
