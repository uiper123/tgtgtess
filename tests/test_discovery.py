"""
Тесты механизма авто-обнаружения серверов тестирования в LAN (UDP Broadcast Discovery).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
from PySide6.QtCore import QByteArray, QCoreApplication, QTimer
from PySide6.QtNetwork import QHostAddress, QUdpSocket
from PySide6.QtWidgets import QApplication

from shared.protocol import DISCOVERY_BEACON_INTERVAL_MS, DISCOVERY_MAGIC, DISCOVERY_PORT


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_discovery_constants():
    assert DISCOVERY_PORT == 9877
    assert DISCOVERY_MAGIC == "TTGTISO_DISCOVERY"
    assert DISCOVERY_BEACON_INTERVAL_MS == 2000


def test_server_discovery_beacon_payload(qapp):
    from server.main import ExamServer, ServerDiscoveryBeacon
    server = ExamServer()
    server.DEFAULT_PORT = 9876
    server._exam_active = True
    server._active_exams = {
        "исп-311": {
            "group": "ИСП-311",
            "test_name": "Контрольная работа",
            "title": "Тест по Python",
        }
    }

    beacon = ServerDiscoveryBeacon(server)
    payload = beacon._get_status_payload()

    assert payload["magic"] == DISCOVERY_MAGIC
    assert payload["type"] == "server_beacon"
    assert payload["tcp_port"] == 9876
    assert payload["exam_active"] is True
    assert "ИСП-311" in payload["groups"]
    assert payload["test_title"] == "Тест по Python"


def test_client_get_current_ip(qapp):
    from client.main import StudentClient
    from client.ui_client import StudentWindow

    client = StudentClient()
    win = StudentWindow(client)

    # 1. Простой ввод IP
    win._ip_input.setEditText("192.168.1.100")
    assert win._get_current_ip() == "192.168.1.100"

    # 2. Ввод IP:port
    win._ip_input.setEditText("192.168.1.100:9876")
    assert win._get_current_ip() == "192.168.1.100:9876"

    # 3. Форматированный пункт из выпадающего списка
    win._ip_input.setEditText("192.168.1.105 (доступен)")
    assert win._get_current_ip() == "192.168.1.105"

    win._ip_input.setEditText("192.168.1.105:9876 (доступен)")
    assert win._get_current_ip() == "192.168.1.105:9876"

    # 4. Пустой ввод
    win._ip_input.setEditText("   ")
    assert win._get_current_ip() == ""


def test_client_on_server_discovered_adds_item(qapp):
    from client.main import StudentClient
    from client.ui_client import StudentWindow

    client = StudentClient()
    win = StudentWindow(client)

    sample_info = {
        "magic": DISCOVERY_MAGIC,
        "type": "server_beacon",
        "tcp_port": 9876,
        "exam_active": True,
        "groups": ["ИСП-311", "ИСП-312"],
        "test_title": "Демо-тестирование",
    }

    win._on_server_discovered("192.168.1.55", 9876, sample_info)

    # Проверяем, что сервер появился в выпадающем списке в формате "IP (доступен)"
    found = False
    for i in range(win._ip_input.count()):
        text = win._ip_input.itemText(i)
        data = win._ip_input.itemData(i)
        if "192.168.1.55" in text and data.get("ip") == "192.168.1.55":
            found = True
            assert text == "192.168.1.55 (доступен)"
            break

    assert found is True
