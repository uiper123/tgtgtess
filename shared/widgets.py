"""
shared/widgets.py — Общие стилизованные виджеты для клиента и сервера.

Решает проблему тёмных popup'ов QComboBox на Linux с тёмной системной темой:
глобальные CSS-селекторы (QComboBox QAbstractItemView) не работают надёжно,
т.к. popup — отдельное top-level окно. Вместо этого мы программно создаём
QListView с прямым стилем и принудительно устанавливаем QPalette.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QComboBox, QListView, QStyledItemDelegate


class _ComboItemDelegate(QStyledItemDelegate):
    """Делегат для элементов списка — гарантирует минимальную высоту строки."""

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), 36))
        return size


class StyledComboBox(QComboBox):
    """
    QComboBox с гарантированно светлым popup-списком.

    Использование — везде, где раньше писали QComboBox():
        combo = StyledComboBox()
        combo.addItems(["A", "B", "C"])
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self._setup_view()

    def _setup_view(self):
        view = QListView(self)
        view.setStyleSheet(
            "QListView {"
            "  background-color: #ffffff;"
            "  border: 1px solid #d6d3d1;"
            "  padding: 4px;"
            "  outline: 0px;"
            "  color: #1c1917;"
            "}"
            "QListView::item {"
            "  background-color: #ffffff;"
            "  color: #1c1917;"
            "  padding: 8px 12px;"
            "  border-radius: 6px;"
            "}"
            "QListView::item:hover {"
            "  background-color: #f5f5f4;"
            "  color: #1c1917;"
            "}"
            "QListView::item:selected {"
            "  background-color: #eff6ff;"
            "  color: #1c1917;"
            "}"
        )

        # Принудительная установка палитры — перебивает любую системную тему
        pal = view.palette()
        pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
        pal.setColor(QPalette.ColorRole.Text, QColor("#1c1917"))
        pal.setColor(QPalette.ColorRole.WindowText, QColor("#1c1917"))
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#eff6ff"))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#1c1917"))
        view.setPalette(pal)

        # Делегат для контроля высоты элементов
        view.setItemDelegate(_ComboItemDelegate(view))

        self.setView(view)

    def showPopup(self):
        """Перехватываем открытие popup, чтобы стилизовать контейнер-обёртку."""
        super().showPopup()

        # Контейнер popup'а — прямой родитель view()
        popup = self.view().parent()
        if popup:
            popup.setStyleSheet(
                "background-color: #ffffff;"
                "border: 1px solid #d6d3d1;"
            )

            # Палитра контейнера — убирает чёрный фон за скруглениями
            pal = popup.palette()
            pal.setColor(QPalette.ColorRole.Window, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            popup.setPalette(pal)
