import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ---------------------------------------------------------------------------
# TTGTiSO-Test — Student Client UI styles
# Design system matches the server side (see server/styles.py for tokens).
# ---------------------------------------------------------------------------

CLIENT_QSS = """
* {
    font-family: "Inter", "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
}

QMainWindow, QWidget#centralWidget, QWidget#scrollContent, QScrollArea#mainScroll {
    background-color: #fafaf9;
    border: none;
}

/* --- Scrollbars --- */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #d6d3d1;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover { background-color: #a8a29e; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }

QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #d6d3d1;
    min-width: 24px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover { background-color: #a8a29e; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
QScrollBar::up-arrow:horizontal, QScrollBar::down-arrow:horizontal,
QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
    background: none;
    border: none;
    width: 0px;
    height: 0px;
}


/* --- Login card --- */
QFrame#loginCard {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 14px;
    padding: 30px;
}

/* --- Inputs --- */
QLineEdit, QComboBox, StyledComboBox {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    padding: 10px 13px;
    font-size: 14px;
    color: #1c1917;
}
QComboBox, StyledComboBox {
    padding-right: 36px;
    min-height: 24px;
}
QLineEdit:hover, QComboBox:hover, StyledComboBox:hover { border-color: #d6d3d1; }
QLineEdit:focus, QComboBox:focus, StyledComboBox:focus {
    border: 1px solid #2563eb;
}
QComboBox QLineEdit, StyledComboBox QLineEdit {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}
QComboBox::drop-down, StyledComboBox::drop-down {
    width: 32px;
    border: none;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
}
QComboBox::down-arrow, StyledComboBox::down-arrow {
    image: url({ICON:chevron-down});
    width: 12px;
    height: 12px;
}
QComboBox QFrame, StyledComboBox QFrame {
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    background-color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    background: #ffffff;
    color: #1c1917;
    border: 1px solid #e7e5e4;
    padding: 6px;
    selection-background-color: #f5f5f4;
    selection-color: #1c1917;
    outline: 0px;
}
QComboBox QAbstractItemView::item {
    background-color: #ffffff;
    background: #ffffff;
    color: #1c1917;
    min-height: 30px;
    padding: 6px 12px;
}
QComboBox QAbstractItemView::item:hover {
    background-color: #f5f5f4;
    background: #f5f5f4;
    color: #1c1917;
}
QComboBox QAbstractItemView::item:selected {
    background-color: #f5f5f4;
    background: #f5f5f4;
    color: #1c1917;
}

/* --- Buttons --- */
QPushButton#connectBtn {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
    padding: 12px;
    border: none;
    border-radius: 8px;
    min-height: 24px;
}
QPushButton#connectBtn:hover { background-color: #1d4ed8; }
QPushButton#connectBtn:disabled {
    background-color: #d6d3d1;
    color: #ffffff;
}

QPushButton#refreshGroupsBtn {
    background-color: #ffffff;
    color: #44403c;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 12px;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    min-height: 22px;
}
QPushButton#refreshGroupsBtn:hover {
    background-color: #fafaf9;
    border-color: #d6d3d1;
}

QPushButton#nextBtn, QPushButton[class="nextBtn"] {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
    padding: 11px 28px;
    border: none;
    border-radius: 8px;
    min-height: 20px;
}
QPushButton#nextBtn:hover, QPushButton[class="nextBtn"]:hover {
    background-color: #1d4ed8;
}

QPushButton#finishBtn, QPushButton[class="finishBtn"] {
    background-color: #16a34a;
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
    padding: 11px 28px;
    border: none;
    border-radius: 8px;
    min-height: 20px;
}
QPushButton#finishBtn:hover, QPushButton[class="finishBtn"]:hover {
    background-color: #15803d;
}

QPushButton#prevBtn, QPushButton[class="secondaryBtn"] {
    background-color: #ffffff;
    color: #44403c;
    font-weight: 600;
    font-size: 14px;
    padding: 11px 28px;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    min-height: 20px;
}
QPushButton#prevBtn:hover, QPushButton[class="secondaryBtn"]:hover {
    background-color: #fafaf9;
    border-color: #d6d3d1;
}

QPushButton[class="primaryBtn"] {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 18px;
    border: none;
    border-radius: 8px;
}
QPushButton[class="primaryBtn"]:hover { background-color: #1d4ed8; }

/* --- Question card --- */
QFrame#questionCard {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 12px;
}

/* --- Radio/Check answer chips --- */
QRadioButton, QCheckBox {
    padding: 14px 18px;
    font-size: 14px;
    color: #1c1917;
    border: 1px solid #d6d3d1;
    border-radius: 10px;
    background-color: #ffffff;
    margin-left: 0px;
}
QRadioButton:hover, QCheckBox:hover {
    background-color: #fafaf9;
    border-color: #a8a29e;
}
QRadioButton:checked, QCheckBox:checked {
    background-color: #eff6ff;
    border-color: #2563eb;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 10px;
    border: 1px solid #d6d3d1;
    background-color: #ffffff;
}
QRadioButton::indicator:checked {
    background-color: #2563eb;
    border: 1px solid #2563eb;
    image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCcgZmlsbD0nd2hpdGUnPjxjaXJjbGUgY3g9JzEyJyBjeT0nMTInIHI9JzYnLz48L3N2Zz4=");
}
QRadioButton::indicator:hover { border-color: #2563eb; }

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #d6d3d1;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border: 1px solid #2563eb;
    image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCcgZmlsbD0nbm9uZScgc3Ryb2tlPSd3aGl0ZScgc3Ryb2tlLXdpZHRoPSc0JyBzdHJva2UtbGluZWNhcD0ncm91bmQnIHN0cm9rZS1saW5lam9pbj0ncm91bmQnPjxwb2x5bGluZSBwb2ludHM9JzIwIDYgOSAxNyA0IDEyJz48L3BvbHlsaW5lPjwvc3ZnPg==");
}
QCheckBox::indicator:hover { border-color: #2563eb; }

/* --- Progress bar --- */
QProgressBar {
    background-color: #e7e5e4;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 4px;
}

/* --- Timer --- */
QLabel#timerLabel {
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 26px;
    font-weight: 600;
    color: #1c1917;
    letter-spacing: -0.5px;
}

/* --- Section headings --- */
QLabel.qTitle {
    font-size: 18px;
    font-weight: 700;
    color: #1c1917;
    letter-spacing: -0.3px;
}
QLabel.qText {
    font-size: 15px;
    color: #44403c;
    line-height: 1.6;
}
QLabel.qCounter {
    font-size: 12px;
    color: #78716c;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

/* --- Dialogs --- */
QDialog {
    background-color: #fafaf9;
}
QMessageBox {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
}
QMessageBox QLabel {
    color: #1c1917;
    font-size: 13.5px;
}
QMessageBox QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 12px;
    padding: 8px 18px;
    border: none;
    border-radius: 8px;
}
QMessageBox QPushButton:hover { background-color: #1d4ed8; }

/* --- Menus --- */
QMenu {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 8px 24px 8px 14px;
    border-radius: 6px;
    color: #1c1917;
    font-size: 13px;
}
QMenu::item:selected {
    background-color: #f5f5f4;
    color: #1c1917;
}
QMenu::separator {
    height: 1px;
    background: #e7e5e4;
    margin: 4px 6px;
}
"""
