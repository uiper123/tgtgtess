GLOBAL_QSS = """
* {
    font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
}
QMainWindow {
    background-color: #f8fafc;
}

/* --- Сайдбар --- */
#sidebar {
    background-color: #1e202b;
    min-width: 260px;
    max-width: 260px;
}
#sidebar QLabel#logoLabel {
    color: #ffffff;
    font-size: 18px;
    font-weight: bold;
    padding: 24px 16px 4px 16px;
}
#sidebar QLabel#logoSub {
    color: #94a3b8;
    font-size: 11px;
    padding: 0 16px 20px 16px;
}
#sidebar QPushButton.navBtn {
    text-align: left;
    padding: 12px 20px;
    border: none;
    border-radius: 8px;
    color: #cbd5e1;
    font-size: 14px;
    background: transparent;
    margin: 2px 10px;
}
#sidebar QPushButton.navBtn:hover {
    background-color: rgba(59, 130, 246, 0.15);
    color: #ffffff;
}
#sidebar QPushButton.navBtn[active="true"] {
    background-color: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    font-weight: bold;
    border-left: 4px solid #3b82f6;
    border-radius: 0px 8px 8px 0px;
    padding-left: 16px;
}
#sidebar QPushButton#createTestBtn {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px;
    border: none;
    border-radius: 10px;
    margin: 8px 14px;
}
#sidebar QPushButton#createTestBtn:hover {
    background-color: #2563eb;
}
#sidebar QLabel#serverStatus {
    color: #94a3b8;
    font-size: 12px;
    padding: 8px 18px 18px 18px;
}

/* --- Карточки --- */
QFrame.card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}
QFrame.statCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 16px;
}

/* --- Поля ввода --- */
QLineEdit {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    color: #1e293b;
}
QLineEdit:focus {
    border: 2px solid #3b82f6;
}
QSpinBox {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px;
    font-size: 13px;
    color: #1e293b;
}
QSpinBox:focus {
    border: 2px solid #3b82f6;
}
QComboBox {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #1e293b;
    min-height: 20px;
}
QComboBox:hover {
    border-color: #cbd5e1;
}
QComboBox:focus {
    border: 2px solid #3b82f6;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left-width: 0px;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #64748b;
    margin-right: 10px;
}
QComboBox QFrame {
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: none;
    selection-background-color: #eff6ff;
    selection-color: #2563eb;
    color: #1e293b;
    padding: 4px;
    outline: 0px;
}
QCheckBox#randomOrderCheck {
    color: #1e293b;
    font-size: 13px;
    font-weight: 600;
    spacing: 8px;
    padding: 9px 10px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background-color: #f9fafb;
}
QCheckBox#randomOrderCheck:hover {
    border-color: #3b82f6;
    background-color: #eff6ff;
}
QCheckBox#randomOrderCheck::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox#randomOrderCheck::indicator:checked {
    background-color: #3b82f6;
    border-color: #3b82f6;
}
QCheckBox#partialScoreCheck {
    color: #1e293b;
    font-size: 13px;
    font-weight: 600;
    spacing: 8px;
    padding: 9px 10px;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    background-color: #f9fafb;
}
QCheckBox#partialScoreCheck:hover {
    border-color: #10b981;
    background-color: #ecfdf5;
}
QCheckBox#partialScoreCheck::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox#partialScoreCheck::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
}

/* --- Кнопки --- */
QPushButton.primaryBtn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
}
QPushButton.primaryBtn:hover {
    background-color: #4f46e5;
}
QPushButton.secondaryBtn {
    background-color: #ffffff;
    color: #3b82f6;
    font-size: 13px;
    font-weight: bold;
    padding: 10px 20px;
    border: 2px solid #3b82f6;
    border-radius: 8px;
}
QPushButton.secondaryBtn:hover {
    background-color: #eff6ff;
}
QPushButton.tableSecondaryBtn {
    background-color: #ffffff;
    color: #2563eb;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 10px;
    border: 1px solid #bfdbfe;
    border-radius: 6px;
    min-height: 24px;
}
QPushButton.tableSecondaryBtn:hover {
    background-color: #eff6ff;
    border-color: #3b82f6;
}
QPushButton.dangerBtn {
    background-color: #ef4444;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
}
QPushButton.dangerBtn:hover {
    background-color: #dc2626;
}
QPushButton.tableDangerBtn {
    background-color: #fee2e2;
    color: #991b1b;
    font-size: 11px;
    font-weight: bold;
    padding: 4px 10px;
    border: 1px solid #fca5a5;
    border-radius: 6px;
    min-height: 24px;
}
QPushButton.tableDangerBtn:hover {
    background-color: #fecaca;
}
QPushButton.successBtn {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 20px;
    border: none;
    border-radius: 8px;
}
QPushButton.successBtn:hover {
    background-color: #059669;
}

/* --- Таблицы --- */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    gridline-color: transparent;
    font-size: 13px;
    color: #334155;
}
QTableWidget::item {
    border-bottom: 1px solid #f1f5f9;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    font-weight: bold;
    font-size: 12px;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
    text-align: left;
}

/* --- Зона сброса файлов --- */
#dropZone {
    background-color: #ffffff;
    border: 2px dashed #cbd5e1;
    border-radius: 16px;
    min-height: 140px;
}
#dropZone:hover {
    border-color: #3b82f6;
    background-color: #f0f7ff;
}

/* --- Лог --- */
QTextEdit#logArea {
    background-color: #1e293b;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
    padding: 10px;
}

/* --- Заголовки --- */
QLabel.sectionTitle {
    font-size: 20px;
    font-weight: bold;
    color: #1e293b;
}
QLabel.sectionSub {
    font-size: 13px;
    color: #64748b;
}

/* --- Dialogs & QMessageBox --- */
QDialog {
    background-color: #ffffff;
}
QDialog QLabel {
    color: #1e293b;
    font-size: 13px;
    background: transparent;
}
QDialog QLineEdit {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 8px 12px;
    color: #1e293b;
    font-size: 13px;
}
QDialog QLineEdit:focus {
    border-color: #3b82f6;
}
QDialog QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 13px;
    padding: 8px 18px;
    border: none;
    border-radius: 8px;
    min-width: 80px;
}
QDialog QPushButton:hover {
    background-color: #2563eb;
}
QMessageBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
}
QMessageBox QLabel {
    color: #1e293b;
    font-size: 14px;
}
QMessageBox QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 12px;
    padding: 8px 16px;
    border: none;
    border-radius: 6px;
}
QMessageBox QPushButton:hover {
    background-color: #2563eb;
}
"""
