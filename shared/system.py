"""
shared/system.py — Системные утилиты для определения путей исполняемых файлов,
фильтрации обновлений по ОС и запуска скриптов обновления.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import tempfile
from typing import List, Optional, Set


def get_current_executable_path() -> str:
    """
    Возвращает абсолютный путь к реальному исполняемому файлу на диске.
    Корректно обрабатывает Nuitka onefile (распаковка в /tmp), PyInstaller,
    standalone-сборки и прямой запуск .py скриптов.
    """
    # 1. Nuitka onefile сохраняет реальный путь к запускаемому бинарнику в переменной окружения
    nuitka_bin = os.environ.get("NUITKA_ONEFILE_BINARY")
    if nuitka_bin:
        return os.path.abspath(nuitka_bin)

    # 2. Скомпилированные сборки (PyInstaller, Nuitka standalone, cx_Freeze)
    if getattr(sys, "frozen", False) and sys.executable:
        return os.path.abspath(sys.executable)

    # 3. Запуск через python script.py
    if sys.argv and sys.argv[0]:
        return os.path.abspath(sys.argv[0])

    if sys.executable:
        return os.path.abspath(sys.executable)

    return ""


def filter_release_assets(
    assets: List[dict],
    server_os: Optional[str] = None,
    connected_client_oses: Optional[Set[str]] = None,
) -> List[dict]:
    """
    Выбирает из списка ассетов релиза GitHub только бинарники под текущую ОС сервера
    и ОС подключенных клиентов. Исключает инсталляторы (Setup.exe).

    Если клиенты не подключены, по умолчанию загружаются файлы только для ОС сервера.
    """
    if server_os is None:
        server_os = platform.system().lower()
    else:
        server_os = server_os.lower()

    if connected_client_oses:
        target_client_oses = {o.lower() for o in connected_client_oses if o}
    else:
        target_client_oses = {server_os}

    filtered = []
    for asset in assets:
        raw_name = asset.get("name", "")
        name = raw_name.lower()

        # Игнорируем setup-инсталляторы (они нужны только для первичной ручной установки)
        if "setup" in name:
            continue

        is_server = "server" in name
        is_student = "student" in name or "client" in name
        is_windows = name.endswith(".exe")
        is_linux = not is_windows

        if is_server:
            if server_os == "windows" and is_windows:
                filtered.append(asset)
            elif server_os == "linux" and is_linux:
                filtered.append(asset)
        elif is_student:
            if "windows" in target_client_oses and is_windows:
                filtered.append(asset)
            elif "linux" in target_client_oses and is_linux:
                filtered.append(asset)

    return filtered


def extract_version_tuple(val: str) -> tuple[int, ...]:
    """
    Извлекает кортеж чисел версии из строки или имени файла (например, 'v1.4.10' -> (1, 4, 10)).
    """
    import re
    match = re.search(r'v?(\d+(?:\.\d+)+)', str(val))
    if match:
        parts = [int(p) for p in match.group(1).split('.')]
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts)
    return (0, 0, 0)


def get_update_files_map(upd_dir: str, version_tag: Optional[str] = None) -> dict[str, str]:
    """
    Сканирует папку updates/ и возвращает словарь путей к клиентским обновлениям:
    {'windows': path_to_student_exe, 'linux': path_to_student_linux}.
    Гарантированно исключает файлы сервера и setup-инсталляторы.
    Выбирает файлы максимальной версии или соответствующие version_tag.
    """
    if not os.path.exists(upd_dir):
        return {}

    target_ver = extract_version_tuple(version_tag) if version_tag else None

    win_candidates = []
    linux_candidates = []

    for f in os.listdir(upd_dir):
        name_lower = f.lower()
        full_path = os.path.join(upd_dir, f)
        if not os.path.isfile(full_path):
            continue

        # Пропускаем серверные файлы и инсталляторы
        if "server" in name_lower or "setup" in name_lower:
            continue

        if "student" in name_lower or "client" in name_lower:
            ver = extract_version_tuple(f)
            mtime = os.path.getmtime(full_path)
            if name_lower.endswith(".exe"):
                win_candidates.append((ver, mtime, full_path))
            else:
                linux_candidates.append((ver, mtime, full_path))

    result = {}

    def select_best(candidates):
        if not candidates:
            return None
        if target_ver and target_ver != (0, 0, 0):
            exact = [c for c in candidates if c[0] == target_ver]
            if exact:
                exact.sort(key=lambda c: c[1], reverse=True)
                return exact[0][2]
        candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
        return candidates[0][2]

    best_win = select_best(win_candidates)
    if best_win:
        result["windows"] = best_win

    best_linux = select_best(linux_candidates)
    if best_linux:
        result["linux"] = best_linux

    return result


def get_server_update_file(
    upd_dir: str,
    target_os: Optional[str] = None,
    version_tag: Optional[str] = None,
) -> Optional[str]:
    """
    Находит в папке updates/ скачанный бинарник сервера для целевой ОС.
    Если указан version_tag, ищет файл соответствующей версии.
    Если найдено несколько файлов, выбирает файл с максимальной версией.
    """
    if target_os is None:
        target_os = platform.system().lower()
    else:
        target_os = target_os.lower()

    if not os.path.exists(upd_dir):
        return None

    candidates = []
    for f in os.listdir(upd_dir):
        name_lower = f.lower()
        if "server" in name_lower and "setup" not in name_lower:
            is_win = name_lower.endswith(".exe")
            if (target_os == "windows" and is_win) or (target_os == "linux" and not is_win):
                full_path = os.path.join(upd_dir, f)
                if os.path.isfile(full_path):
                    ver = extract_version_tuple(f)
                    mtime = os.path.getmtime(full_path)
                    candidates.append((ver, mtime, full_path))

    if not candidates:
        return None

    if version_tag:
        target_ver = extract_version_tuple(version_tag)
        if target_ver != (0, 0, 0):
            exact = [c for c in candidates if c[0] == target_ver]
            if exact:
                exact.sort(key=lambda c: c[1], reverse=True)
                return exact[0][2]

    candidates.sort(key=lambda c: (c[0], c[1]), reverse=True)
    return candidates[0][2]


def run_updater_script(current_exe: str, update_file: str) -> bool:
    """
    Запускает платформо-независимый скрипт замены бинарника и перезапуска приложения.
    Скрипт создаётся в системной temp-директории и отделяется от родительского процесса.
    """
    if not current_exe or not os.path.exists(update_file):
        return False

    tmp_dir = tempfile.gettempdir()
    exe_dir = os.path.dirname(current_exe)

    if platform.system() == "Windows":
        fd, updater_script = tempfile.mkstemp(suffix=".bat", prefix="edutest_update_", dir=tmp_dir)
        os.close(fd)
        with open(updater_script, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write("setlocal enabledelayedexpansion\n")
            f.write("set /a count=0\n")
            f.write(":retry\n")
            f.write("timeout /t 1 /nobreak > nul\n")
            f.write(f'del "{current_exe}" > nul 2>&1\n')
            f.write(f'if exist "{current_exe}" (\n')
            f.write("    set /a count+=1\n")
            f.write("    if !count! lss 20 goto retry\n")
            f.write(")\n")
            f.write(f'move /y "{update_file}" "{current_exe}" > nul 2>&1\n')
            if exe_dir:
                f.write(f'cd /d "{exe_dir}"\n')
            f.write(f'start "" "{current_exe}"\n')
            f.write('del "%~f0"\n')

        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            ["cmd.exe", "/c", updater_script],
            shell=False,
            creationflags=flags,
        )
        return True
    else:
        fd, updater_script = tempfile.mkstemp(suffix=".sh", prefix="edutest_update_", dir=tmp_dir)
        os.close(fd)
        with open(updater_script, "w", encoding="utf-8") as f:
            f.write("#!/bin/bash\n")
            f.write("sleep 2\n")
            f.write(f'if [ -f "{update_file}" ]; then\n')
            f.write(f'    cp -f "{update_file}" "{current_exe}" 2>/dev/null || mv -f "{update_file}" "{current_exe}"\n')
            f.write(f'    chmod +x "{current_exe}"\n')
            f.write(f'    rm -f "{update_file}"\n')
            f.write("fi\n")
            if exe_dir:
                f.write(f'cd "{exe_dir}" || true\n')
            f.write(f'nohup "{current_exe}" >/dev/null 2>&1 &\n')
            f.write('rm -f "$0"\n')

        os.chmod(updater_script, 0o755)
        subprocess.Popen(
            ["/bin/bash", updater_script],
            start_new_session=True,
        )
        return True
