"""
End-to-end интеграционные тесты системы обновлений.

Не используют GUI (Qt в headless-режиме через QCoreApplication), но
поднимают реальный TCP-сервер, подключают реальный клиентский сокет,
гоняют байты сквозь весь pipeline:

    [server] send_update_to_socket
       │
       ▼  TCP (loopback)
       │
    [client] _handle_update_start
             _handle_update_chunk × N
             _handle_update_complete
                  └─ verify_signature + sha256 + write .new

И отдельно — реальный запуск updater-скрипта на Linux в песочнице.
"""

from __future__ import annotations

import base64
import json
import os
import platform
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Делаем корень репо importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Qt в headless-режиме
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PySide6 = pytest.importorskip("PySide6")
pytest.importorskip("cryptography")


def _require_qtwidgets():
    """Тесты, импортирующие client.main, нуждаются в QtWidgets
    (он тянет ui_client.py). В headless CI без libEGL — пропускаем."""
    try:
        import PySide6.QtWidgets
    except ImportError as e:
        pytest.skip(f"QtWidgets not available (likely missing libEGL): {e}")

from PySide6.QtCore import QByteArray, QCoreApplication, QTimer
from PySide6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket

from shared.protocol import pack_message
from shared.security import (
    load_private_key,
    sha256_hex,
    sign_bytes,
    verify_signature,
)


def _sign(payload: bytes, priv_path) -> str:
    """Хелпер: загрузить приватный ключ из PEM-файла и подписать payload."""
    sk = load_private_key(priv_path)
    return sign_bytes(sk, payload)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    """Один QCoreApplication на весь модуль — Qt не любит много экземпляров."""
    app = QCoreApplication.instance() or QCoreApplication(sys.argv)
    yield app


@pytest.fixture
def keypair(monkeypatch, tmp_path):
    """
    Свежая пара ключей, public подложен туда, где его найдёт security.find_public_key_path().
    Каждый тест изолирован.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    sk = Ed25519PrivateKey.generate()
    pk = sk.public_key()

    priv_pem = sk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = pk.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    priv_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
    priv_path.write_bytes(priv_pem)
    pub_path.write_bytes(pub_pem)

    # security.has_public_key() / verify_signature() ищут ключ через
    # find_public_key_path() — перенаправляем в нашу временную папку.
    from shared import security as sec_mod
    monkeypatch.setattr(sec_mod, "find_public_key_path", lambda: pub_path)

    return {"priv": priv_path, "pub": pub_path, "priv_pem": priv_pem}


@pytest.fixture
def fake_update_payload():
    """Похожий на бинарник кусок данных — 200 КБ случайных байтов."""
    return os.urandom(200 * 1024)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


MAX_MSG = 64 * 1024 * 1024


def receive_packets(sock: QTcpSocket, app: QCoreApplication, n: int, timeout_ms=5000):
    """
    Читает n length-prefixed JSON-пакетов с сокета, прокачивая Qt event-loop.
    Возвращает список распарсенных dict-ов.
    """
    buf = QByteArray()
    packets: list[dict] = []

    deadline = QTimer()
    deadline.setSingleShot(True)
    deadline.start(timeout_ms)

    while len(packets) < n and deadline.isActive():
        app.processEvents()
        if sock.bytesAvailable():
            buf.append(sock.readAll())

        while buf.size() >= 4:
            msg_len = struct.unpack("!I", bytes(buf[:4]))[0]
            if buf.size() < 4 + msg_len:
                break
            raw = bytes(buf[4 : 4 + msg_len])
            buf.remove(0, 4 + msg_len)
            packets.append(json.loads(raw.decode("utf-8")))

    return packets


# ---------------------------------------------------------------------------
# 1. Signing roundtrip (low-level)
# ---------------------------------------------------------------------------


def test_sign_and_verify_roundtrip_real_keys(keypair, fake_update_payload):
    """Подпись частным ключом → проверка публичным → True. Один из базовых
    инвариантов всей цепочки."""
    sig = _sign(fake_update_payload, keypair["priv"])
    assert verify_signature(fake_update_payload, sig) is True


def test_tampered_payload_rejected(keypair, fake_update_payload):
    """Меняем один байт — подпись становится невалидной."""
    sig = _sign(fake_update_payload, keypair["priv"])
    tampered = bytearray(fake_update_payload)
    tampered[12345] ^= 0xFF
    assert verify_signature(bytes(tampered), sig) is False


def test_wrong_signature_rejected(keypair, fake_update_payload, tmp_path):
    """Подпись от другого ключа → отвергается."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    evil_sk = Ed25519PrivateKey.generate()
    evil_pem = evil_sk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    evil_priv = tmp_path / "evil.pem"
    evil_priv.write_bytes(evil_pem)
    evil_sig = _sign(fake_update_payload, evil_priv)
    assert verify_signature(fake_update_payload, evil_sig) is False


# ---------------------------------------------------------------------------
# 2. Real TCP roundtrip — server.send_update_to_socket → client receives
# ---------------------------------------------------------------------------


@pytest.fixture
def tcp_pair(qapp):
    """Поднимает QTcpServer на loopback и подключает к нему QTcpSocket.
    Возвращает (server_side_sock, client_side_sock)."""
    server = QTcpServer()
    assert server.listen(QHostAddress.LocalHost, 0)
    port = server.serverPort()

    client_sock = QTcpSocket()
    client_sock.connectToHost(QHostAddress.LocalHost, port)

    # Ждём connect
    deadline = 0
    while not server.hasPendingConnections() and deadline < 100:
        qapp.processEvents()
        deadline += 1

    assert server.hasPendingConnections(), "TCP-соединение не установилось"
    server_sock = server.nextPendingConnection()

    # Ждём пока клиент тоже узнает что connected
    while client_sock.state() != QTcpSocket.ConnectedState and deadline < 200:
        qapp.processEvents()
        deadline += 1

    yield server_sock, client_sock

    client_sock.disconnectFromHost()
    server_sock.disconnectFromHost()
    server.close()


def _build_signed_chunk_packets(payload: bytes, priv_path, chunk_size=64 * 1024):
    """Имитирует то, что send_update_to_socket собирает на сервере."""
    sig = _sign(payload, priv_path)
    h = sha256_hex(payload)
    total = (len(payload) + chunk_size - 1) // chunk_size

    pkts = [{
        "status": "update_start",
        "total_chunks": total,
        "sha256": h,
        "signature": sig,
        "sig_algo": "ed25519",
        "filename": "test_update.bin",
    }]
    for i in range(total):
        chunk = payload[i * chunk_size : (i + 1) * chunk_size]
        pkts.append({
            "status": "update_chunk",
            "chunk_index": i,
            "chunk_data": base64.b64encode(chunk).decode("ascii"),
        })
    pkts.append({"status": "update_complete", "sha256": h, "signature": sig, "sig_algo": "ed25519"})
    return pkts, h, sig


def test_chunked_update_full_roundtrip(tcp_pair, qapp, keypair, fake_update_payload):
    """Полный chunked-цикл: сервер шлёт start + chunks + complete, клиент
    собирает в файл, проверяет хэш и подпись."""
    server_sock, client_sock = tcp_pair
    pkts, expected_hash, expected_sig = _build_signed_chunk_packets(
        fake_update_payload, keypair["priv"]
    )

    # Шлём все пакеты
    for p in pkts:
        server_sock.write(pack_message(p))
    server_sock.flush()

    # Принимаем
    received = receive_packets(client_sock, qapp, n=len(pkts))
    assert len(received) == len(pkts)

    # Восстанавливаем payload
    chunks = [base64.b64decode(p["chunk_data"]) for p in received if p["status"] == "update_chunk"]
    reconstructed = b"".join(chunks)
    assert reconstructed == fake_update_payload

    # И всё это валидно подписано
    assert sha256_hex(reconstructed) == expected_hash
    assert verify_signature(reconstructed, expected_sig) is True


def test_chunked_update_with_tampered_chunk_rejected(qapp, keypair, fake_update_payload):
    """Сервер шлёт правильную подпись, но один чанк подменён — клиент
    после сборки должен увидеть несовпадение хэша."""
    pkts, expected_hash, expected_sig = _build_signed_chunk_packets(
        fake_update_payload, keypair["priv"]
    )
    # Подменяем 2-й чанк
    bad = bytearray(base64.b64decode(pkts[2]["chunk_data"]))
    bad[0] ^= 0xFF
    pkts[2]["chunk_data"] = base64.b64encode(bytes(bad)).decode("ascii")

    chunks = [base64.b64decode(p["chunk_data"]) for p in pkts if p["status"] == "update_chunk"]
    reconstructed = b"".join(chunks)
    assert sha256_hex(reconstructed) != expected_hash, \
        "Хэш должен не совпасть — иначе вся проверка целостности бесполезна"
    assert verify_signature(reconstructed, expected_sig) is False


# ---------------------------------------------------------------------------
# 3. Client-side guards — without real Qt, just calling the methods
# ---------------------------------------------------------------------------


def test_client_rejects_legacy_update_without_signature(monkeypatch, fake_update_payload, tmp_path):
    """
    `_save_update_file` должен отказаться записывать .new, если в пакете
    нет signature, а у клиента есть public key (то есть он умеет проверять).
    """
    _require_qtwidgets()
    pytest.importorskip("PySide6.QtCore")
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication(sys.argv)

    # Имитируем что у клиента есть public key (verify включается)
    from shared import security as sec
    monkeypatch.setattr(sec, "has_public_key", lambda: True)

    # Перехватываем sys.argv[0] чтобы .new путь шёл в tmp_path
    fake_exe = tmp_path / "fake_client"
    fake_exe.write_bytes(b"ORIGINAL")
    monkeypatch.setattr(sys, "argv", [str(fake_exe)])

    from client.main import StudentClient
    client = StudentClient()

    bad_packet = {
        "status": "update_available",
        "payload": base64.b64encode(fake_update_payload).decode("ascii"),
        # signature, sha256 — отсутствуют
    }
    ok = client._save_update_file(bad_packet)
    assert ok is False, "Клиент с public_key обязан отвергать неподписанные обновления"
    assert not (tmp_path / "fake_client.new").exists(), ".new не должен быть создан"


def test_client_rejects_legacy_update_with_wrong_hash(monkeypatch, fake_update_payload, tmp_path, keypair):
    """Подпись валидная, но хэш в пакете не совпадает с фактическим payload."""
    _require_qtwidgets()
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication(sys.argv)

    from shared import security as sec
    monkeypatch.setattr(sec, "has_public_key", lambda: True)

    fake_exe = tmp_path / "fake_client2"
    fake_exe.write_bytes(b"ORIGINAL")
    monkeypatch.setattr(sys, "argv", [str(fake_exe)])

    from client.main import StudentClient
    client = StudentClient()

    sig = _sign(fake_update_payload, keypair["priv"])
    pkt = {
        "status": "update_available",
        "payload": base64.b64encode(fake_update_payload).decode("ascii"),
        "signature": sig,
        "sha256": "deadbeef" * 8,  # неправильный
    }
    ok = client._save_update_file(pkt)
    assert ok is False, "Клиент обязан отвергать пакет с неправильным sha256"


def test_client_accepts_correctly_signed_update(monkeypatch, fake_update_payload, tmp_path, keypair):
    """Happy path: всё валидно → .new создан."""
    _require_qtwidgets()
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication(sys.argv)

    fake_exe = tmp_path / "fake_client3"
    fake_exe.write_bytes(b"ORIGINAL")
    monkeypatch.setattr(sys, "argv", [str(fake_exe)])

    from client.main import StudentClient
    client = StudentClient()

    sig = _sign(fake_update_payload, keypair["priv"])
    pkt = {
        "status": "update_available",
        "payload": base64.b64encode(fake_update_payload).decode("ascii"),
        "signature": sig,
        "sha256": sha256_hex(fake_update_payload),
    }
    ok = client._save_update_file(pkt)
    assert ok is True
    new_path = Path(str(fake_exe) + ".new")
    assert new_path.exists()
    assert new_path.read_bytes() == fake_update_payload


# ---------------------------------------------------------------------------
# 4. Updater script — physically executable on Linux
# ---------------------------------------------------------------------------


@pytest.mark.skipif(platform.system() == "Windows", reason="Linux-only physical test")
def test_linux_updater_script_actually_swaps_binary(monkeypatch, tmp_path):
    """
    Реальная проверка: создаём fake old + fake new (бинарник под видом
    shell-скрипта чтобы запуск не падал), дёргаем _run_updater,
    реально ждём 3 секунды (updater делает sleep 2), проверяем swap.
    """
    _require_qtwidgets()
    import time

    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication(sys.argv)

    fake_exe = tmp_path / "edutest_fake"
    fake_exe.write_bytes(b"#!/bin/bash\necho OLD\n")
    os.chmod(fake_exe, 0o755)
    fake_new = tmp_path / "edutest_fake.new"
    fake_new.write_bytes(b"#!/bin/bash\necho NEW VERSION\n")
    monkeypatch.setattr(sys, "argv", [str(fake_exe)])

    # Заглушаем уход приложения — pytest сам не упадёт
    from PySide6.QtWidgets import QApplication
    monkeypatch.setattr(QApplication, "quit", lambda *a, **k: None)
    monkeypatch.setattr(sys, "exit", lambda *a, **k: None)
    monkeypatch.setattr(platform, "system", lambda: "Linux")

    from client.main import StudentClient
    client = StudentClient()

    client._run_updater()

    # Updater делает sleep 2 — ждём чуть больше
    time.sleep(3.0)

    assert fake_exe.exists(), "Старый бинарник должен остаться (новый перемещён на его место)"
    actual = fake_exe.read_bytes()
    assert actual == b"#!/bin/bash\necho NEW VERSION\n", (
        f"Swap не сработал. Содержимое: {actual!r}"
    )
    assert not fake_new.exists(), ".new должен быть удалён после mv"


# ---------------------------------------------------------------------------
# 5. Windows updater script — content sanity check (без выполнения)
# ---------------------------------------------------------------------------


def test_windows_updater_script_has_proper_quoting(monkeypatch, tmp_path):
    """Скрипт .bat должен правильно квотировать пути с пробелами
    (типичная Windows-проблема `C:\\Program Files\\...`)."""
    _require_qtwidgets()
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication(sys.argv)

    fake_exe = tmp_path / "Program Files" / "EduTest" / "client.exe"
    fake_exe.parent.mkdir(parents=True)
    fake_exe.write_bytes(b"old")
    (tmp_path / "Program Files" / "EduTest" / "client.exe.new").write_bytes(b"new")
    monkeypatch.setattr(sys, "argv", [str(fake_exe)])
    monkeypatch.setattr(platform, "system", lambda: "Windows")

    written_scripts: list[str] = []

    def fake_popen(cmd, *a, **kw):
        # Грабим путь скрипта из cmd и сохраняем содержимое
        if isinstance(cmd, list):
            for arg in cmd:
                if isinstance(arg, str) and arg.endswith(".bat") and os.path.exists(arg):
                    written_scripts.append(open(arg).read())
        class FakeProc:
            pid = 0
        return FakeProc()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(sys, "exit", lambda *a, **k: None)

    from client.main import StudentClient
    client = StudentClient()

    client._run_updater()

    assert written_scripts, "Bat-скрипт должен был быть создан"
    script = written_scripts[0]
    assert '"' in script, "Скрипт должен квотировать пути"
    # Путь содержит пробел → он обязан быть в кавычках, иначе del/move сломаются
    assert f'"{fake_exe}"' in script, \
        f"Путь с пробелом не закавычен. Скрипт:\n{script[:500]}"


def test_server_check_for_updates(monkeypatch):
    """
    Проверяет, что check_for_updates правильно парсит ответ от GitHub API.
    """
    _require_qtwidgets()
    import urllib.request

    from server.main import ExamServer

    class MockResponse:
        def __init__(self, data_bytes):
            self.data = data_bytes
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
        def read(self):
            return self.data

    # Ветка 1: Доступна новая версия
    def mock_urlopen_new(*args, **kwargs):
        return MockResponse(b'{"tag_name": "v9.9.9", "assets": []}')

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_new)
    server = ExamServer()
    data, error = server.check_for_updates()
    assert error is None
    assert data is not None
    assert data["tag_name"] == "v9.9.9"

    # Ветка 2: Версия актуальная
    from shared.version import VERSION
    def mock_urlopen_latest(*args, **kwargs):
        return MockResponse(f'{{"tag_name": "v{VERSION}", "assets": []}}'.encode())

    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen_latest)
    data, error = server.check_for_updates()
    assert error == "latest"
    assert data is not None
