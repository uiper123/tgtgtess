import re


def get_scaled_qss(qss_text: str, scale_factor: float) -> str:
    """
    Масштабирует числовые значения в QSS (px) согласно коэффициенту.
    """
    scale_factor = float(scale_factor)
    if scale_factor == 1.0:
        return qss_text

    def replace_px(match):
        value = float(match.group(1))
        scaled_value = max(1, int(round(value * scale_factor)))
        return f"{scaled_value}px"

    # Регулярное выражение для поиска значений в px
    scaled_qss = re.sub(r'(\d+(?:\.\d+)?)px', replace_px, qss_text)
    return scaled_qss


def inject_icon_paths(qss: str) -> str:
    """Заменяет {ICON:name} плейсхолдеры на абсолютные file:// пути к
    SVG-файлам в shared/icons/. Использовать перед setStyleSheet."""
    import os
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    def resolve(name):
        return os.path.abspath(os.path.join(icons_dir, name)).replace(os.sep, "/")
    return (
        qss.replace("{ICON:chevron-down}", resolve("chevron-down.svg"))
           .replace("{ICON:chevron-up}", resolve("chevron-up.svg"))
    )
