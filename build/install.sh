#!/bin/bash
# Скрипт автоустановки EduTest Pro Student для Alt Linux

# Проверка прав суперпользователя (root)
if [ "$EUID" -ne 0 ]; then
  echo "Пожалуйста, запустите скрипт от имени суперпользователя (root) через sudo."
  exit 1
fi

echo "=== Начало установки EduTest Pro Student ==="

# Определение директорий
INSTALL_DIR="/opt/test_system_student"
BINARY_SOURCE="./dist/student/TTGTiSO-Test-student"
DESKTOP_FILE="/usr/share/applications/edutest-student.desktop"

# 1. Создание папки установки
mkdir -p "$INSTALL_DIR"

# 2. Копирование бинарного файла
if [ -f "$BINARY_SOURCE" ]; then
  echo "Копирование исполняемого файла..."
  cp "$BINARY_SOURCE" "$INSTALL_DIR/TTGTiSO-Test-student"
else
  # Попытка найти во вложенных папках
  if [ -f "./dist/student/TTGTiSO-Test-student" ]; then
    cp "./dist/student/TTGTiSO-Test-student" "$INSTALL_DIR/TTGTiSO-Test-student"
  else
    echo "Ошибка: Исполняемый файл не найден в $BINARY_SOURCE."
    exit 1
  fi
fi

# 3. Установка прав доступа (защита от перезаписи студентами)
echo "Настройка прав доступа..."
chown -R root:root "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR/TTGTiSO-Test-student"

# 4. Копирование иконки если она есть
if [ -f "./image.png" ]; then
  cp "./image.png" "$INSTALL_DIR/icon.png"
elif [ -f "./image.ico" ]; then
  cp "./image.ico" "$INSTALL_DIR/icon.ico"
fi

# 5. Создание файла .desktop для интеграции в меню
echo "Создание ярлыка в системном меню..."
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Version=1.0
Type=Application
Name=EduTest Pro Student
Comment=Система тестирования студентов
Exec=$INSTALL_DIR/TTGTiSO-Test-student
Icon=$INSTALL_DIR/icon.png
Terminal=false
Categories=Education;
StartupNotify=true
EOF

chmod 644 "$DESKTOP_FILE"

echo "=== Установка успешно завершена! ==="
echo "Приложение доступно в меню 'Обучение/Образование' (Education)."
