#!/usr/bin/env bash
# run_test.sh — Запуск сервера преподавателя и клиента студента для тестирования
# Использование: bash run_test.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${SCRIPT_DIR}/venv/bin/python"

if [ ! -f "$VENV" ]; then
    echo "Ошибка: виртуальное окружение не найдено. Запустите:"
    echo "  python3 -m venv venv && ./venv/bin/pip install PySide6"
    exit 1
fi

export DISPLAY="${DISPLAY:-:1}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"

echo "=== TTGTiSO-Test — Тестовый запуск ==="
echo "Запуск сервера преподавателя..."
"$VENV" "${SCRIPT_DIR}/server/main.py" &
SERVER_PID=$!
echo "  PID сервера: $SERVER_PID"

sleep 2

echo "Запуск клиента студента..."
"$VENV" "${SCRIPT_DIR}/client/main.py" &
CLIENT_PID=$!
echo "  PID клиента: $CLIENT_PID"

echo ""
echo "Оба приложения запущены."
echo "Для остановки: kill $SERVER_PID $CLIENT_PID"
echo "Или нажмите Ctrl+C"

trap "kill $SERVER_PID $CLIENT_PID 2>/dev/null; echo 'Остановлено.'; exit 0" INT TERM
wait
