from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from shared.widgets import StyledComboBox


# Severity buckets used by the log filter. Matches the keyword colour rules
# in ui_server._append_log so the two stay in sync.
SEVERITY_KEYWORDS = {
    "error":   ["ошибка", "error", "отклонён", "отключился", "отменено", "не найден"],
    "warning": ["внимание", "пропущено", "предупреждение", "не активен", "ожидание"],
    "success": ["успешно", "завершен", "подключился", "success", "сохранен"],
    "network": ["скачивание", "передача", "загрузка", "обновления"],
}


def _classify_severity(text: str) -> str:
    low = text.lower()
    for sev, words in SEVERITY_KEYWORDS.items():
        if any(w in low for w in words):
            return sev
    return "info"


class LogsMixin:
    def _build_logs_page(self):
        self.logs_page = QWidget()
        main_layout = QVBoxLayout(self.logs_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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

        # --- Фильтры журнала ---
        filter_card = QFrame()
        filter_card.setObjectName("logFilterCard")
        filter_card.setStyleSheet(
            "QFrame#logFilterCard { background-color: #ffffff;"
            " border: 1px solid #e7e5e4; border-radius: 12px; }"
        )
        f_lay = QHBoxLayout(filter_card)
        f_lay.setContentsMargins(14, 10, 14, 10)
        f_lay.setSpacing(12)

        self._log_search = QLineEdit()
        self._log_search.setPlaceholderText("Поиск по тексту записи…")
        self._log_search.setStyleSheet(
            "QLineEdit { padding: 8px 12px; font-size: 13px;"
            " border: 1px solid #e7e5e4; border-radius: 8px;"
            " background-color: #ffffff; color: #1c1917; }"
            "QLineEdit:focus { border: 1px solid #2563eb; }"
        )
        self._log_search.textChanged.connect(self._render_log_entries)
        f_lay.addWidget(self._log_search, 3)

        self._log_severity = StyledComboBox()
        self._log_severity.addItems([
            "Все события",
            "Ошибки",
            "Предупреждения",
            "Успехи",
            "Сеть / обновления",
            "Информация",
        ])
        self._log_severity.currentIndexChanged.connect(self._render_log_entries)
        f_lay.addWidget(self._log_severity, 1)

        layout.addWidget(filter_card)

        # Зона с текстом логов
        card = QFrame()
        card.setProperty("class", "card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        self._log = QTextEdit()
        self._log.setObjectName("logArea")
        self._log.setReadOnly(True)
        self._log.setStyleSheet(
            "border: none; padding: 12px;"
            " font-family: 'Consolas', 'Courier New', monospace;"
            " font-size: 13px; color: #44403c;"
        )
        card_layout.addWidget(self._log)

        layout.addWidget(card, 1)

        # Persistent log buffer — survives filter changes.
        if not hasattr(self, "_log_entries"):
            self._log_entries = []

        main_layout.addWidget(content)
        self.stacked_widget.addWidget(self.logs_page)

    # ------------------------------------------------------------------
    # Filter helpers
    # ------------------------------------------------------------------
    def _severity_for_filter_index(self, idx: int) -> str | None:
        return {
            0: None,
            1: "error",
            2: "warning",
            3: "success",
            4: "network",
            5: "info",
        }.get(idx)

    def _render_log_entries(self):
        """Re-render the log area applying the active search + severity filters."""
        if not hasattr(self, "_log"):
            return
        query = self._log_search.text().strip().lower() if hasattr(self, "_log_search") else ""
        wanted = self._severity_for_filter_index(
            self._log_severity.currentIndex() if hasattr(self, "_log_severity") else 0
        )

        self._log.clear()
        for entry in self._log_entries:
            if wanted and entry["severity"] != wanted:
                continue
            if query and query not in entry["text"].lower():
                continue
            self._log.append(entry["html"])

    def _clear_logs(self):
        self._log_entries = []
        self._log.clear()
        self.exam_server.log_message.emit("Логи очищены")
