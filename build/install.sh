#!/usr/bin/env bash
# install.sh — Скрипт автоустановки клиента студента для Alt Linux / Arch / etc.
# Запуск: sudo bash install.sh

set -euo pipefail

APP_NAME="edutest-student"
APP_DISPLAY_NAME="EduTest Pro - Студент"
INSTALL_DIR="/opt/edutest-pro"
BINARY_NAME="edutest-student"
DESKTOP_FILE="/usr/share/applications/${APP_NAME}.desktop"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/../dist/student"

# --- Проверка прав ---
if [ "$(id -u)" -ne 0 ]; then
    echo "Ошибка: запустите скрипт с правами root (sudo)."
    exit 1
fi

# --- Проверка наличия бинарника ---
if [ ! -f "${DIST_DIR}/${BINARY_NAME}" ]; then
    echo "Ошибка: бинарный файл не найден: ${DIST_DIR}/${BINARY_NAME}"
    echo "Сначала запустите: python build_all.py"
    exit 1
fi

echo "=== Установка ${APP_DISPLAY_NAME} ==="

# --- Копирование файлов ---
echo "[1/3] Копирование файлов в ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
cp "${DIST_DIR}/${BINARY_NAME}" "${INSTALL_DIR}/"

# Попытка найти иконку
ICON_SOURCE="${SCRIPT_DIR}/../Gemini_Generated_Image_xjemh4xjemh4xjem.png"
if [ -f "$ICON_SOURCE" ]; then
    cp "$ICON_SOURCE" "${INSTALL_DIR}/icon.png"
fi

# --- Установка прав доступа ---
echo "[2/3] Установка прав доступа..."
chmod 755 "${INSTALL_DIR}/${BINARY_NAME}"
chown -R root:root "${INSTALL_DIR}"

# --- Создание .desktop файла ---
echo "[3/3] Создание ярлыка в системном меню..."
cat > "${DESKTOP_FILE}" << EOL
[Desktop Entry]
Version=1.0
Type=Application
Name=${APP_DISPLAY_NAME}
Comment=Система тестирования студентов EduTest Pro
Exec=${INSTALL_DIR}/${BINARY_NAME}
Icon=${INSTALL_DIR}/icon.png
Terminal=false
Categories=Education;
StartupNotify=true
EOL

chmod 644 "${DESKTOP_FILE}"

if command -v update-desktop-database &>/dev/null; then
    update-desktop-database /usr/share/applications/ 2>/dev/null || true
fi

echo ""
echo "=== Установка завершена ==="
echo "Приложение доступно в меню под именем: ${APP_DISPLAY_NAME}"
