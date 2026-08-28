import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ---------------------------------------------------------------------------
# TTGTiSO-Test — Server UI styles
#
# Design system v2 ("Editorial"):
#   * Warm stone neutrals (Tailwind stone scale) instead of cool slate.
#   * Single calm accent — blue-600 (#2563eb), used sparingly.
#   * Charcoal sidebar (#1c1917) with subtle active states (no left bars).
#   * Flat surfaces, no gradients, no drop shadows.
#   * Slightly tighter radii (cards 12px, controls 8px).
#   * Lighter font-weights — semibold (600) over heavy (800).
# ---------------------------------------------------------------------------

GLOBAL_QSS = """
* {
    font-family: "Inter", "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
}

QMainWindow {
    background-color: #fafaf9;
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
QScrollBar::handle:vertical:hover {
    background-color: #a8a29e;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
    height: 0px;
    width: 0px;
    subcontrol-position: top;
    subcontrol-origin: margin;
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
QScrollBar::handle:horizontal:hover {
    background-color: #a8a29e;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: none;
    background: none;
    width: 0px;
    height: 0px;
    subcontrol-position: left;
    subcontrol-origin: margin;
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


/* --- Sidebar --- */
#sidebar {
    background-color: #1c1917;
    min-width: 248px;
    max-width: 248px;
    border-right: 1px solid #292524;
}
#sidebar QLabel#logoLabel {
    color: #fafaf9;
    font-size: 18px;
    font-weight: 700;
    padding: 24px 20px 2px 20px;
    letter-spacing: -0.2px;
}
#sidebar QLabel#logoSub {
    color: #78716c;
    font-size: 11px;
    font-weight: 500;
    padding: 0 20px 22px 20px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}
#sidebar QPushButton.navBtn {
    text-align: left;
    padding: 11px 18px;
    border: none;
    border-radius: 8px;
    color: #a8a29e;
    font-size: 13.5px;
    font-weight: 500;
    background: transparent;
    margin: 2px 12px;
}
#sidebar QPushButton.navBtn:hover {
    background-color: rgba(255, 255, 255, 0.05);
    color: #fafaf9;
}
#sidebar QPushButton.navBtn[active="true"] {
    background-color: rgba(255, 255, 255, 0.08);
    color: #fafaf9;
    font-weight: 600;
}
#sidebar QPushButton#createTestBtn {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 10px;
    border: none;
    border-radius: 8px;
    margin: 10px 14px;
}
#sidebar QPushButton#createTestBtn:hover {
    background-color: #1d4ed8;
}
#sidebar QLabel#serverStatus {
    color: #d6d3d1;
    font-size: 12px;
    font-weight: 500;
    padding: 12px 20px 18px 20px;
    border-top: 1px solid #292524;
}

/* --- Cards --- */
QFrame.card {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 12px;
}
QFrame.statCard {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 12px;
    padding: 18px;
}

/* --- Inputs --- */
QLineEdit {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 13px;
    color: #1c1917;
}
QLineEdit:hover { border-color: #d6d3d1; }
QLineEdit:focus { border: 1px solid #2563eb; }

QSpinBox {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 13px;
    color: #1c1917;
}
QSpinBox:hover { border-color: #d6d3d1; }
QSpinBox:focus { border: 1px solid #2563eb; }
QSpinBox::up-button, QSpinBox::down-button {
    subcontrol-origin: border;
    width: 18px;
    border: none;
    background: transparent;
}
QSpinBox::up-button { subcontrol-position: top right; margin-top: 2px; margin-right: 4px; }
QSpinBox::down-button { subcontrol-position: bottom right; margin-bottom: 2px; margin-right: 4px; }
QSpinBox::up-arrow { image: url({ICON:chevron-up}); width: 9px; height: 9px; }
QSpinBox::down-arrow { image: url({ICON:chevron-down}); width: 9px; height: 9px; }
QSpinBox::up-arrow:hover, QSpinBox::down-arrow:hover { width: 10px; height: 10px; }

QComboBox, StyledComboBox {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    color: #1c1917;
    min-height: 22px;
}
QComboBox:hover, StyledComboBox:hover { border-color: #d6d3d1; }
QComboBox:focus, StyledComboBox:focus { border: 1px solid #2563eb; }
QComboBox::drop-down, StyledComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left-width: 0px;
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

/* --- Checkboxes --- */
QCheckBox {
    color: #1c1917;
    font-size: 13px;
    font-weight: 500;
    spacing: 10px;
    padding: 9px 12px;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    background-color: #ffffff;
}
QCheckBox:hover {
    border-color: #d6d3d1;
    background-color: #fafaf9;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #d6d3d1;
    background-color: #ffffff;
}
QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
    image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAyNCAyNCcgZmlsbD0nbm9uZScgc3Ryb2tlPSd3aGl0ZScgc3Ryb2tlLXdpZHRoPSc0JyBzdHJva2UtbGluZWNhcD0ncm91bmQnIHN0cm9rZS1saW5lam9pbj0ncm91bmQnPjxwb2x5bGluZSBwb2ludHM9JzIwIDYgOSAxNyA0IDEyJz48L3BvbHlsaW5lPjwvc3ZnPg==");
}

/* --- Buttons --- */
QPushButton.primaryBtn {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 18px;
    border: none;
    border-radius: 8px;
}
QPushButton.primaryBtn:hover { background-color: #1d4ed8; }
QPushButton.primaryBtn:pressed { background-color: #1e40af; }

QPushButton.secondaryBtn {
    background-color: #ffffff;
    color: #44403c;
    font-size: 13px;
    font-weight: 600;
    padding: 9px 18px;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
}
QPushButton.secondaryBtn:hover {
    background-color: #fafaf9;
    border-color: #d6d3d1;
}

QPushButton.tableSecondaryBtn {
    background-color: #ffffff;
    color: #44403c;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border: 1px solid #e7e5e4;
    border-radius: 6px;
    min-height: 26px;
}
QPushButton.tableSecondaryBtn:hover {
    background-color: #fafaf9;
    border-color: #d6d3d1;
}

QPushButton.dangerBtn {
    background-color: #dc2626;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 18px;
    border: none;
    border-radius: 8px;
}
QPushButton.dangerBtn:hover { background-color: #b91c1c; }

QPushButton.tableDangerBtn {
    background-color: #ffffff;
    color: #b91c1c;
    font-size: 12px;
    font-weight: 600;
    padding: 6px 12px;
    border: 1px solid #fecaca;
    border-radius: 6px;
    min-height: 26px;
}
QPushButton.tableDangerBtn:hover {
    background-color: #fef2f2;
    border-color: #fca5a5;
}

QPushButton.successBtn {
    background-color: #16a34a;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 18px;
    border: none;
    border-radius: 8px;
}
QPushButton.successBtn:hover { background-color: #15803d; }

/* --- Tables --- */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 12px;
    gridline-color: transparent;
    font-size: 13px;
    color: #44403c;
    padding: 4px;
    selection-background-color: #f5f5f4;
    selection-color: #1c1917;
    outline: 0;
}
QTableWidget::item {
    border-bottom: 1px solid #f5f5f4;
    padding: 8px 12px;
}
QTableWidget::item:hover {
    background-color: #fafaf9;
}
QTableWidget::item:selected {
    background-color: #f5f5f4;
    color: #1c1917;
}
QTableWidget QWidget {
    background-color: transparent;
}
QHeaderView::section {
    background-color: #ffffff;
    color: #78716c;
    font-weight: 600;
    font-size: 11.5px;
    padding: 12px 12px;
    border: none;
    border-bottom: 1px solid #e7e5e4;
    text-align: left;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

/* --- Scroll content --- */
#scrollContent {
    background-color: #fafaf9;
}

/* --- Drop zone --- */
#dropZone {
    background-color: #ffffff;
    border: 2px dashed #d6d3d1;
    border-radius: 12px;
    min-height: 150px;
}
#dropZone:hover {
    border-color: #a8a29e;
    background-color: #fafaf9;
}

/* --- Log area --- */
QTextEdit#logArea {
    background-color: #1c1917;
    color: #d6d3d1;
    border: none;
    border-radius: 10px;
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 12px;
    padding: 14px;
}

/* --- Section titles --- */
QLabel.sectionTitle {
    font-size: 22px;
    font-weight: 700;
    color: #1c1917;
    letter-spacing: -0.4px;
}
QLabel.sectionSub {
    font-size: 13px;
    color: #78716c;
    font-weight: 500;
}

/* --- Dialogs --- */
QDialog {
    background-color: #fafaf9;
}
QDialog QLabel {
    color: #1c1917;
    font-size: 13px;
    font-weight: 500;
    background: transparent;
}
QDialog QLineEdit {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    padding: 9px 12px;
    color: #1c1917;
    font-size: 13px;
}
QDialog QLineEdit:focus { border-color: #2563eb; }
QDialog QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    padding: 9px 18px;
    border: none;
    border-radius: 8px;
    min-width: 80px;
}
QDialog QPushButton:hover { background-color: #1d4ed8; }

/* --- File Dialog & Views --- */
QFileDialog {
    background-color: #fafaf9;
    color: #1c1917;
}
QFileDialog QLabel {
    color: #44403c;
    font-size: 12px;
}
QFileDialog QTreeView, QFileDialog QListView, QTreeView, QListView, QAbstractItemView {
    background-color: #ffffff;
    background: #ffffff;
    color: #1c1917;
    border: 1px solid #e7e5e4;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #e0f2fe;
    selection-color: #0369a1;
    alternate-background-color: #fafaf9;
    outline: 0;
}
QAbstractItemView::viewport,
QTreeView::viewport,
QListView::viewport,
QTableView::viewport,
QFileDialog QAbstractItemView::viewport,
QFileDialog QTreeView::viewport,
QFileDialog QListView::viewport {
    background-color: #ffffff;
    background: #ffffff;
    color: #1c1917;
}
QFileDialog QWidget#qt_sidebar,
QFileDialog QFrame#qt_sidebar,
QFileDialog QListView#sidebar {
    background-color: #f5f5f4;
    color: #1c1917;
    border-right: 1px solid #e7e5e4;
}
QTreeView::item, QListView::item {
    color: #1c1917;
    padding: 6px;
    border-radius: 4px;
    min-height: 24px;
}
QTreeView::item:hover, QListView::item:hover {
    background-color: #f5f5f4;
    color: #1c1917;
}
QTreeView::item:selected, QListView::item:selected {
    background-color: #e0f2fe;
    color: #0369a1;
}
QFileDialog QHeaderView::section {
    background-color: #f5f5f4;
    color: #57534e;
    font-weight: 600;
    font-size: 11px;
    padding: 6px 8px;
    border: none;
    border-bottom: 1px solid #e7e5e4;
}
QFileDialog QToolButton {
    background-color: #ffffff;
    border: 1px solid #e7e5e4;
    border-radius: 6px;
    padding: 6px 10px;
    margin: 2px;
    color: #44403c;
}
QFileDialog QToolButton:hover {
    background-color: #f5f5f4;
    border-color: #d6d3d1;
}
QFileDialog QSplitter::handle {
    background-color: #e7e5e4;
    width: 2px;
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

/* --- Tooltip --- */
QToolTip {
    background-color: #1c1917;
    color: #fafaf9;
    border: none;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}
"""
