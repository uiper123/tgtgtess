CLIENT_QSS = """
* {
    font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
}
QMainWindow, QWidget#centralWidget {
    background-color: #f8fafc;
}

/* --- Login card --- */
QFrame#loginCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 30px;
}

/* --- Inputs --- */
QLineEdit, QComboBox {
    background-color: #f9fafb;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    color: #1e293b;
}
QComboBox {
    padding-right: 38px;
    min-height: 22px;
}
QLineEdit:focus, QComboBox:focus {
    border: 2px solid #3b82f6;
}
QComboBox QLineEdit {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}
QComboBox::drop-down {
    width: 34px;
    border: none;
    border-left: 1px solid #e2e8f0;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox::down-arrow {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%2364758b' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");
    width: 14px;
    height: 14px;
}
QComboBox QFrame {
    border: 1px solid #cbd5e1;
    background-color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: none;
    padding: 4px;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
    outline: 0px;
}
QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 6px 10px;
}

/* --- Buttons --- */
QPushButton#connectBtn {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 15px;
    padding: 14px;
    border: none;
    border-radius: 10px;
    min-height: 22px;
}
QPushButton#connectBtn:hover {
    background-color: #2563eb;
}
QPushButton#connectBtn:disabled {
    background-color: #94a3b8;
}
QPushButton#refreshGroupsBtn {
    background-color: #ffffff;
    color: #3b82f6;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 12px;
    border: 2px solid #bfdbfe;
    border-radius: 8px;
    min-height: 22px;
}
QPushButton#refreshGroupsBtn:hover {
    background-color: #eff6ff;
    border-color: #3b82f6;
}
QPushButton#nextBtn {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 32px;
    border: none;
    border-radius: 10px;
}
QPushButton#nextBtn:hover {
    background-color: #2563eb;
}
QPushButton#finishBtn {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 32px;
    border: none;
    border-radius: 10px;
}
QPushButton#finishBtn:hover {
    background-color: #059669;
}

/* --- Question card --- */
QFrame#questionCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
}

/* --- Radio / Checkbox --- */
QRadioButton, QCheckBox {
    padding: 14px 20px;
    font-size: 14px;
    color: #334155;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    background-color: #ffffff;
    margin-left: 52px;
}
QRadioButton:hover, QCheckBox:hover {
    background-color: #eff6ff;
    border-color: #3b82f6;
}
QRadioButton:checked, QCheckBox:checked {
    background-color: #f0f7ff;
    border-color: #3b82f6;
}

QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border-radius: 11px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QRadioButton::indicator:checked {
    background-color: #3b82f6;
    border: 2px solid #3b82f6;
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'><circle cx='12' cy='12' r='6'/></svg>");
}
QRadioButton::indicator:hover {
    border-color: #3b82f6;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 5px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #10b981;
    border: 2px solid #10b981;
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'><polyline points='20 6 9 17 4 12'></polyline></svg>");
}
QCheckBox::indicator:hover {
    border-color: #10b981;
}


/* --- Progress bar --- */
QProgressBar {
    background-color: #e2e8f0;
    border: none;
    border-radius: 6px;
    height: 12px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #10b981;
    border-radius: 6px;
}

/* --- Timer --- */
QLabel#timerLabel {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 28px;
    font-weight: bold;
    color: #1e293b;
}

/* --- Section titles --- */
QLabel.qTitle {
    font-size: 18px;
    font-weight: bold;
    color: #1e293b;
}
QLabel.qText {
    font-size: 15px;
    color: #334155;
    line-height: 1.5;
}
QLabel.qCounter {
    font-size: 13px;
    color: #64748b;
    font-weight: bold;
}

/* --- Dialogs & QMessageBox --- */
QDialog {
    background-color: #f8fafc;
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
