"""
tests/test_system.py — Тесты для shared/system.py:
- Определение пути исполняемого файла (Nuitka onefile, frozen, py-скрипт)
- Фильтрация ассетов обновлений под целевую ОС
- Сканирование пакетов обновлений в updates/ с выбором наивысшей версии
- Генерация и запуск скриптов обновления
"""

import sys
import time

from shared.system import (
    extract_version_tuple,
    filter_release_assets,
    get_current_executable_path,
    get_server_update_file,
    get_update_files_map,
    run_updater_script,
)


def test_extract_version_tuple():
    assert extract_version_tuple("TTGTiSO-Test-server-v1.4.10") == (1, 4, 10)
    assert extract_version_tuple("TTGTiSO-Test-server-v1.4.7") == (1, 4, 7)
    assert extract_version_tuple("1.4.10") == (1, 4, 10)
    assert extract_version_tuple("v1.4.10") == (1, 4, 10)
    assert extract_version_tuple("unknown") == (0, 0, 0)


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


def test_get_update_files_map_picks_highest_version(tmp_path):
    (tmp_path / "TTGTiSO-Test-student-v1.4.7.exe").write_bytes(b"old_win")
    (tmp_path / "TTGTiSO-Test-student-v1.4.10.exe").write_bytes(b"new_win")
    (tmp_path / "TTGTiSO-Test-student-v1.4.7").write_bytes(b"old_lin")
    (tmp_path / "TTGTiSO-Test-student-v1.4.10").write_bytes(b"new_lin")

    files_map = get_update_files_map(str(tmp_path))
    assert "windows" in files_map
    assert files_map["windows"].endswith("student-v1.4.10.exe")
    assert "linux" in files_map
    assert files_map["linux"].endswith("student-v1.4.10")


def test_get_server_update_file_picks_highest_version(tmp_path):
    (tmp_path / "TTGTiSO-Test-server-v1.4.7.exe").write_bytes(b"old_win")
    (tmp_path / "TTGTiSO-Test-server-v1.4.10.exe").write_bytes(b"new_win")
    (tmp_path / "TTGTiSO-Test-server-v1.4.7").write_bytes(b"old_lin")
    (tmp_path / "TTGTiSO-Test-server-v1.4.10").write_bytes(b"new_lin")

    win_file = get_server_update_file(str(tmp_path), target_os="windows")
    assert win_file is not None
    assert win_file.endswith("server-v1.4.10.exe")

    lin_file = get_server_update_file(str(tmp_path), target_os="linux")
    assert lin_file is not None
    assert lin_file.endswith("server-v1.4.10")


def test_get_server_update_file_with_target_tag(tmp_path):
    (tmp_path / "TTGTiSO-Test-server-v1.4.7").write_bytes(b"v7")
    (tmp_path / "TTGTiSO-Test-server-v1.4.9").write_bytes(b"v9")
    (tmp_path / "TTGTiSO-Test-server-v1.4.10").write_bytes(b"v10")

    file_v9 = get_server_update_file(str(tmp_path), target_os="linux", version_tag="1.4.9")
    assert file_v9 is not None
    assert file_v9.endswith("server-v1.4.9")


def test_run_updater_script_missing_files(tmp_path):
    assert not run_updater_script("", str(tmp_path / "nonexistent.new"))
    assert not run_updater_script(str(tmp_path / "exe"), str(tmp_path / "nonexistent.new"))
