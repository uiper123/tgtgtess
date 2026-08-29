from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from shared.version import VERSION


class AboutMixin:
    def _build_about_page(self):
        self.about_page = QWidget()
        layout = QVBoxLayout(self.about_page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel("Сведения о программе")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #1c1917;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(24)

        # Info Card
        info_card = QFrame()
        info_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 12px; }")
        info_lay = QVBoxLayout(info_card)
        info_lay.setContentsMargins(24, 24, 24, 24)
        info_lay.setSpacing(12)

        app_title = QLabel(f"TTGTiSO-Test v{VERSION}")
        app_title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2563eb; border: none;")
        info_lay.addWidget(app_title)

        desc = QLabel(
            "Интерактивная система тестирования студентов.\n"
            "Позволяет создавать тесты, проводить их в реальном времени по локальной сети и автоматически выставлять оценки."
        )
        desc.setStyleSheet("font-size: 15px; color: #44403c; border: none; line-height: 1.5;")
        desc.setWordWrap(True)
        info_lay.addWidget(desc)

        c_layout.addWidget(info_card)

        # Changelog Card
        changelog_card = QFrame()
        changelog_card.setStyleSheet("QFrame { background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 12px; }")
        ch_lay = QVBoxLayout(changelog_card)
        ch_lay.setContentsMargins(24, 24, 24, 24)
        ch_lay.setSpacing(16)

        ch_title = QLabel("Что нового в текущей версии?")
        ch_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1c1917; border: none;")
        ch_lay.addWidget(ch_title)

        changes = [
            ("✨ Новые типы вопросов", "Добавлены типы «Упорядочивание» (Drag-and-Drop) и «Пропуски в тексте»."),
            ("🧠 Умная проверка текста", "Система теперь игнорирует лишние пробелы, регистр и поддерживает несколько правильных вариантов для одного пропуска (разделитель «|»)."),
            ("💅 Улучшенный дизайн", "Карточки при перетаскивании получили анимации, чёткие индикаторы позиционирования и современные стили."),
            ("📝 Подсказки преподавателям", "В редакторе вопросов появились автоматические подсказки по синтаксису и созданию сложных тестов."),
        ]

        for emoji, text in changes:
            row = QHBoxLayout()
            row.setAlignment(Qt.AlignTop)

            lbl_emoji = QLabel(emoji)
            lbl_emoji.setStyleSheet("font-size: 15px; font-weight: bold; color: #1c1917; border: none;")
            lbl_emoji.setFixedWidth(200)

            lbl_text = QLabel(text)
            lbl_text.setStyleSheet("font-size: 14px; color: #57534e; border: none;")
            lbl_text.setWordWrap(True)

            row.addWidget(lbl_emoji)
            row.addWidget(lbl_text, 1)
            ch_lay.addLayout(row)

        c_layout.addWidget(changelog_card)
        c_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)
        self.stacked_widget.addWidget(self.about_page)
