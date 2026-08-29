"""
tests/test_system.py — Тесты для shared/system.py:
- Определение пути исполняемого файла (Nuitka onefile, frozen, py-скрипт)
- Фильтрация ассетов обновлений под целевую ОС
- Сканирование пакетов обновлений в updates/
- Генерация и запуск скриптов обновления
"""

import os
import sys

import pytest

from shared.system import (
    filter_release_assets,
    get_current_executable_path,
    get_server_update_file,
    get_update_files_map,
    run_updater_script,
)


def test_get_current_executable_path_nuitka(monkeypatch):
    monkeypatch.setenv("NUITKA_ONEFILE_BINARY", "/home/user/App/TTGTiSO-Test-server")
    monkeypatch.setattr(sys, "argv", ["/tmp/onefile_123/server"])
    path = get_current_executable_path()
    assert path == "/home/user/App/TTGTiSO-Test-server"


def test_get_current_executable_path_frozen(monkeypatch):
    monkeypatch.delenv("NUITKA_ONEFILE_BINARY", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/opt/edutest/client")
    path = get_current_executable_path()
    assert path == "/opt/edutest/client"


def test_get_current_executable_path_script(monkeypatch):
    monkeypatch.delenv("NUITKA_ONEFILE_BINARY", raising=False)
    if hasattr(sys, "frozen"):
        monkeypatch.delattr(sys, "frozen")
    monkeypatch.setattr(sys, "argv", ["server/main.py"])
    path = get_current_executable_path()
    assert path.endswith("server/main.py")


def test_filter_release_assets_linux_server_no_clients():
    assets = [
        {"name": "TTGTiSO-Test-server-v1.4.8.exe", "browser_download_url": "http://example.com/s_win"},
        {"name": "TTGTiSO-Test-student-v1.4.8.exe", "browser_download_url": "http://example.com/c_win"},
        {"name": "EduTestStudent_Setup-v1.4.8.exe", "browser_download_url": "http://example.com/setup"},
        {"name": "TTGTiSO-Test-server-v1.4.8", "browser_download_url": "http://example.com/s_lin"},
        {"name": "TTGTiSO-Test-student-v1.4.8", "browser_download_url": "http://example.com/c_lin"},
    ]

    filtered = filter_release_assets(assets, server_os="linux", connected_client_oses=None)
    names = [a["name"] for a in filtered]

    # Должны быть выбраны только Linux сервер и Linux студент, setup пропущен
    assert names == ["TTGTiSO-Test-server-v1.4.8", "TTGTiSO-Test-student-v1.4.8"]


def test_filter_release_assets_windows_server_no_clients():
    assets = [
        {"name": "TTGTiSO-Test-server-v1.4.8.exe", "browser_download_url": "http://example.com/s_win"},
        {"name": "TTGTiSO-Test-student-v1.4.8.exe", "browser_download_url": "http://example.com/c_win"},
        {"name": "EduTestStudent_Setup-v1.4.8.exe", "browser_download_url": "http://example.com/setup"},
        {"name": "TTGTiSO-Test-server-v1.4.8", "browser_download_url": "http://example.com/s_lin"},
        {"name": "TTGTiSO-Test-student-v1.4.8", "browser_download_url": "http://example.com/c_lin"},
    ]

    filtered = filter_release_assets(assets, server_os="windows", connected_client_oses=set())
    names = [a["name"] for a in filtered]

    # Должны быть выбраны только Windows сервер и Windows студент, setup пропущен
    assert names == ["TTGTiSO-Test-server-v1.4.8.exe", "TTGTiSO-Test-student-v1.4.8.exe"]


def test_filter_release_assets_linux_server_with_windows_students():
    assets = [
        {"name": "TTGTiSO-Test-server-v1.4.8.exe", "browser_download_url": "http://example.com/s_win"},
        {"name": "TTGTiSO-Test-student-v1.4.8.exe", "browser_download_url": "http://example.com/c_win"},
        {"name": "EduTestStudent_Setup-v1.4.8.exe", "browser_download_url": "http://example.com/setup"},
        {"name": "TTGTiSO-Test-server-v1.4.8", "browser_download_url": "http://example.com/s_lin"},
        {"name": "TTGTiSO-Test-student-v1.4.8", "browser_download_url": "http://example.com/c_lin"},
    ]

    filtered = filter_release_assets(assets, server_os="linux", connected_client_oses={"windows"})
    names = [a["name"] for a in filtered]

    # Linux сервер + Windows студент для подключенного клиента
    assert names == ["TTGTiSO-Test-student-v1.4.8.exe", "TTGTiSO-Test-server-v1.4.8"]


def test_get_update_files_map(tmp_path):
    (tmp_path / "TTGTiSO-Test-server-v1.4.8.exe").write_bytes(b"server_win")
    (tmp_path / "TTGTiSO-Test-student-v1.4.8.exe").write_bytes(b"student_win")
    (tmp_path / "EduTestStudent_Setup-v1.4.8.exe").write_bytes(b"setup_win")
    (tmp_path / "TTGTiSO-Test-server-v1.4.8").write_bytes(b"server_lin")
    (tmp_path / "TTGTiSO-Test-student-v1.4.8").write_bytes(b"student_lin")

    files_map = get_update_files_map(str(tmp_path))
    assert "windows" in files_map
    assert files_map["windows"].endswith("student-v1.4.8.exe")
    assert "linux" in files_map
    assert files_map["linux"].endswith("student-v1.4.8")


def test_get_server_update_file(tmp_path):
    (tmp_path / "TTGTiSO-Test-server-v1.4.8.exe").write_bytes(b"server_win")
    (tmp_path / "TTGTiSO-Test-server-v1.4.8").write_bytes(b"server_lin")

    win_file = get_server_update_file(str(tmp_path), target_os="windows")
    assert win_file is not None
    assert win_file.endswith("server-v1.4.8.exe")

    lin_file = get_server_update_file(str(tmp_path), target_os="linux")
    assert lin_file is not None
    assert lin_file.endswith("server-v1.4.8")


def test_run_updater_script_missing_files(tmp_path):
    assert not run_updater_script("", str(tmp_path / "nonexistent.new"))
    assert not run_updater_script(str(tmp_path / "exe"), str(tmp_path / "nonexistent.new"))
