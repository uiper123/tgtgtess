CLIENT_QSS = """
* {
    font-family: "Segoe UI", "Inter", "Outfit", "Roboto", sans-serif;
}

QMainWindow, QWidget#centralWidget {
    background-color: #f8fafc;
}

/* --- Премиальные скроллбары --- */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    min-height: 20px;
    border-radius: 4px;
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
    height: 8px;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    min-width: 20px;
    border-radius: 4px;
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

/* --- Входная карточка --- */
QFrame#loginCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 20px;
    padding: 35px;
}

/* --- Ввод текста и селекторы --- */
QLineEdit, QComboBox {
    background-color: #ffffff;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 11px 14px;
    font-size: 14px;
    color: #0f172a;
}
QComboBox {
    padding-right: 40px;
    min-height: 24px;
}
QLineEdit:focus, QComboBox:focus {
    border: 2px solid #6366f1;
}
QComboBox QLineEdit {
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}
QComboBox::drop-down {
    width: 36px;
    border: none;
    border-left: 1px solid #e2e8f0;
    border-top-right-radius: 10px;
    border-bottom-right-radius: 10px;
}
QComboBox::down-arrow {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%2364758b' stroke-width='3' stroke-linecap='round' stroke-linejoin='round'><polyline points='6 9 12 15 18 9'/></svg>");
    width: 14px;
    height: 14px;
}
QComboBox QFrame {
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background-color: #ffffff;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: none;
    padding: 6px;
    selection-background-color: #eff6ff;
    selection-color: #6366f1;
    outline: 0px;
}
QComboBox QAbstractItemView::item {
    min-height: 32px;
    padding: 6px 12px;
}

/* --- Премиальные Кнопки --- */
QPushButton#connectBtn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 15px;
    padding: 14px;
    border: none;
    border-radius: 12px;
    min-height: 24px;
}
QPushButton#connectBtn:hover {
    background-color: #4f46e5;
}
QPushButton#connectBtn:disabled {
    background-color: #94a3b8;
}

QPushButton#refreshGroupsBtn {
    background-color: #ffffff;
    color: #6366f1;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 14px;
    border: 2px solid #c7d2fe;
    border-radius: 10px;
    min-height: 22px;
}
QPushButton#refreshGroupsBtn:hover {
    background-color: #eff6ff;
    border-color: #6366f1;
}

QPushButton#nextBtn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 34px;
    border: none;
    border-radius: 12px;
}
QPushButton#nextBtn:hover {
    background-color: #4f46e5;
}

QPushButton#finishBtn {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 34px;
    border: none;
    border-radius: 12px;
}
QPushButton#finishBtn:hover {
    background-color: #059669;
}

QPushButton.primaryBtn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: bold;
    font-size: 14px;
    padding: 12px 34px;
    border: none;
    border-radius: 12px;
}
QPushButton.primaryBtn:hover {
    background-color: #4f46e5;
}

/* --- Карточка Вопроса --- */
QFrame#questionCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
}

/* --- Радио-кнопки и Чекбоксы (Адаптивные интерактивные кнопки) --- */
QRadioButton, QCheckBox {
    padding: 14px 20px;
    font-size: 14px;
    color: #334155;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    background-color: #ffffff;
    margin-left: 20px;
}
QRadioButton:hover, QCheckBox:hover {
    background-color: #eff6ff;
    border-color: #6366f1;
}
QRadioButton:checked, QCheckBox:checked {
    background-color: #f0f7ff;
    border-color: #6366f1;
}

QRadioButton::indicator {
    width: 20px;
    height: 20px;
    border-radius: 11px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QRadioButton::indicator:checked {
    background-color: #6366f1;
    border: 2px solid #6366f1;
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='white'><circle cx='12' cy='12' r='6'/></svg>");
}
QRadioButton::indicator:hover {
    border-color: #6366f1;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 6px;
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

/* --- Прогресс-бар --- */
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

/* --- Таймер --- */
QLabel#timerLabel {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 28px;
    font-weight: bold;
    color: #0f172a;
}

/* --- Заголовки разделов --- */
QLabel.qTitle {
    font-size: 19px;
    font-weight: 800;
    color: #0f172a;
}
QLabel.qText {
    font-size: 15px;
    color: #334155;
    line-height: 1.6;
}
QLabel.qCounter {
    font-size: 13px;
    color: #64748b;
    font-weight: bold;
}

/* --- Диалоги и Системные уведомления --- */
QDialog {
    background-color: #f8fafc;
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

def get_scaled_qss(qss_text, scale_factor):
    import re
    scale_factor = float(scale_factor)
    if scale_factor == 1.0:
        return qss_text
    
    def replace_px(match):
        value = float(match.group(1))
        scaled_value = max(1, int(round(value * scale_factor)))
        return f"{scaled_value}px"
    
    # Scale all px values in the client QSS safely
    scaled_qss = re.sub(r'(\d+)px', replace_px, qss_text)
    return scaled_qss

