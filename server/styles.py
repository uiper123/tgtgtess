import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from shared.styles import get_scaled_qss

GLOBAL_QSS = """
* {
    font-family: "Segoe UI", "Inter", "Outfit", "Roboto", sans-serif;
}

QMainWindow {
    background-color: #f8fafc;
}

/* --- Красивые кастомные скроллбары --- */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 10px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    min-height: 24px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 10px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    min-width: 24px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

/* --- Премиальный Сайдбар --- */
#sidebar {
    background-color: #0f172a; /* Глубокий темно-синий */
    min-width: 260px;
    max-width: 260px;
    border-right: 1px solid #1e293b;
}
#sidebar QLabel#logoLabel {
    color: #ffffff;
    font-size: 20px;
    font-weight: 800;
    padding: 24px 20px 4px 20px;
    letter-spacing: 0.5px;
}
#sidebar QLabel#logoSub {
    color: #64748b;
    font-size: 11px;
    font-weight: 600;
    padding: 0 20px 24px 20px;
    text-transform: uppercase;
}
#sidebar QPushButton.navBtn {
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-radius: 8px;
    color: #94a3b8;
    font-size: 14px;
    font-weight: 500;
    background: transparent;
    margin: 3px 14px;
}
#sidebar QPushButton.navBtn:hover {
    background-color: rgba(99, 102, 241, 0.1);
    color: #f8fafc;
}
#sidebar QPushButton.navBtn[active="true"] {
    background-color: rgba(99, 102, 241, 0.15);
    color: #818cf8;
    font-weight: bold;
    border-left: 4px solid #6366f1;
    border-radius: 0px 8px 8px 0px;
    padding-left: 16px;
}
#sidebar QPushButton#createTestBtn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px;
    border: none;
    border-radius: 10px;
    margin: 12px 18px;
}
#sidebar QPushButton#createTestBtn:hover {
    background-color: #4f46e5;
}
#sidebar QLabel#serverStatus {
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
    padding: 12px 20px 20px 20px;
    border-top: 1px solid #1e293b;
}

/* --- Премиальные Карточки --- */
QFrame.card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
}
QFrame.statCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 18px;
}

/* --- Красивые поля ввода и спинбоксы --- */
QLineEdit {
    background-color: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    color: #0f172a;
}
QLineEdit:focus {
    border: 2px solid #6366f1;
}

QSpinBox {
    background-color: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 13px;
    color: #0f172a;
}
QSpinBox:focus {
    border: 2px solid #6366f1;
}

QComboBox {
    background-color: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    color: #0f172a;
    min-height: 22px;
}
QComboBox:hover {
    border-color: #cbd5e1;
}
QComboBox:focus {
    border: 2px solid #6366f1;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 32px;
    border-left-width: 0px;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #64748b;
    margin-right: 12px;
}
QComboBox QFrame {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background-color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: none;
    selection-background-color: #eff6ff;
    selection-color: #6366f1;
    color: #0f172a;
    padding: 6px;
    outline: 0px;
}

/* --- Красивые Чекбоксы --- */
QCheckBox#randomOrderCheck, QCheckBox#partialScoreCheck {
    color: #0f172a;
    font-size: 13px;
    font-weight: 600;
    spacing: 10px;
    padding: 10px 14px;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    background-color: #ffffff;
}
QCheckBox#randomOrderCheck:hover {
    border-color: #6366f1;
    background-color: #f5f3ff;
}
QCheckBox#randomOrderCheck::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox#randomOrderCheck::indicator:checked {
    background-color: #6366f1;
    border-color: #6366f1;
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
}

QCheckBox#partialScoreCheck:hover {
    border-color: #10b981;
    background-color: #ecfdf5;
}
QCheckBox#partialScoreCheck::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox#partialScoreCheck::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
}

/* --- Премиальные Кнопки --- */
QPushButton.primaryBtn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 22px;
    border: none;
    border-radius: 10px;
}
QPushButton.primaryBtn:hover {
    background-color: #4f46e5;
}

QPushButton.secondaryBtn {
    background-color: #ffffff;
    color: #475569;
    font-size: 13px;
    font-weight: bold;
    padding: 10px 22px;
    border: 2px solid #cbd5e1;
    border-radius: 10px;
}
QPushButton.secondaryBtn:hover {
    background-color: #f8fafc;
    border-color: #94a3b8;
}

QPushButton.tableSecondaryBtn {
    background-color: #ffffff;
    color: #4f46e5;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 12px;
    border: 1px solid #c7d2fe;
    border-radius: 8px;
    min-height: 26px;
}
QPushButton.tableSecondaryBtn:hover {
    background-color: #e0e7ff;
    border-color: #6366f1;
}

QPushButton.dangerBtn {
    background-color: #ef4444;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 22px;
    border: none;
    border-radius: 10px;
}
QPushButton.dangerBtn:hover {
    background-color: #dc2626;
}

QPushButton.tableDangerBtn {
    background-color: #fee2e2;
    color: #991b1b;
    font-size: 11px;
    font-weight: 700;
    padding: 6px 12px;
    border: 1px solid #fca5a5;
    border-radius: 8px;
    min-height: 26px;
}
QPushButton.tableDangerBtn:hover {
    background-color: #fecaca;
}

QPushButton.successBtn {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 22px;
    border: none;
    border-radius: 10px;
}
QPushButton.successBtn:hover {
    background-color: #059669;
}

/* --- Красивые Таблицы --- */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    gridline-color: #e2e8f0;
    font-size: 13px;
    color: #334155;
    padding: 6px;
    selection-background-color: #eef2ff;
    selection-color: #1e293b;
    outline: 0;
}
QTableWidget::item {
    border-bottom: 1px solid #f1f5f9;
    padding: 6px 12px;
}
QTableWidget::item:hover {
    background-color: #f8fafc;
}
QTableWidget::item:selected {
    background-color: #eef2ff;
    color: #1e293b;
}
QTableWidget QWidget {
    background-color: transparent;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    font-weight: bold;
    font-size: 12px;
    padding: 12px;
    border: none;
    border-right: 1px solid #cbd5e1;
    border-bottom: 2px solid #cbd5e1;
    text-align: left;
}

/* --- Контейнер прокрутки --- */
#scrollContent {
    background-color: #f8fafc;
}

/* --- Зона сброса файлов --- */
#dropZone {
    background-color: #ffffff;
    border: 2px dashed #cbd5e1;
    border-radius: 20px;
    min-height: 150px;
}
#dropZone:hover {
    border-color: #6366f1;
    background-color: #f5f3ff;
}

/* --- Лог --- */
QTextEdit#logArea {
    background-color: #0f172a;
    color: #94a3b8;
    border: none;
    border-radius: 10px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    padding: 12px;
}

/* --- Заголовки --- */
QLabel.sectionTitle {
    font-size: 22px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.2px;
}
QLabel.sectionSub {
    font-size: 13px;
    color: #64748b;
    font-weight: 500;
}

/* --- Красивые Диалоги и Окна --- */
QDialog {
    background-color: #f8fafc;
}
QDialog QLabel {
    color: #0f172a;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}
QDialog QLineEdit {
    background-color: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 8px 12px;
    color: #0f172a;
    font-size: 13px;
}
QDialog QLineEdit:focus {
    border-color: #6366f1;
}
QDialog QPushButton {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
    min-width: 90px;
}
QDialog QPushButton:hover {
    background-color: #4f46e5;
}

QMessageBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
}
QMessageBox QLabel {
    color: #0f172a;
    font-size: 14px;
}
QMessageBox QPushButton {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
    padding: 8px 18px;
    border: none;
    border-radius: 8px;
}
QMessageBox QPushButton:hover {
    background-color: #4f46e5;
}
"""

