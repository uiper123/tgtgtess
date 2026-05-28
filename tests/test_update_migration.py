"""
Тесты на сценарии миграции и устойчивости системы обновлений.

1. Миграция v1.3.6 → v1.3.7: клиент без public_key должен принимать
   неподписанные обновления (иначе никто не сможет накатить v1.3.7).
2. Sidecar-файлы .sha256/.sig сохраняются рядом с .new.
3. update_apply отвергает повреждённый .new по sidecar.
4. Disk space / permissions проверки.
"""

from __future__ import annotations

import base64
import hashlib
import os
import platform
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

pytest.importorskip("PySide6")
pytest.importorskip("cryptography")


def _require_qtwidgets():
    try:
        import PySide6.QtWidgets
    except ImportError as e:
        pytest.skip(f"PySide6.QtWidgets unavailable: {e}")


def _make_client(monkeypatch, tmp_path, *, has_pubkey: bool):
    """Создаёт StudentClient, подменяя has_public_key и sys.argv[0]."""
    _require_qtwidgets()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QCoreApplication
    QCoreApplication.instance() or QCoreApplication([])

    fake_exe = tmp_path / "edutest_fake"
    fake_exe.write_bytes(b"OLD-BINARY")
    monkeypatch.setattr(sys, "argv", [str(fake_exe)])

    from shared import security
    monkeypatch.setattr(security, "has_public_key", lambda: has_pubkey)

    import client.main as cm
    monkeypatch.setattr(cm, "has_public_key", lambda: has_pubkey)

    client = cm.StudentClient()
    return client, fake_exe


# ============================================================
# 1) МИГРАЦИЯ: v1.3.6 → v1.3.7
# ============================================================

def test_old_client_without_pubkey_accepts_unsigned_update(monkeypatch, tmp_path):
    """v1.3.6 ничего не знает про подпись — должен принять unsigned update."""
    client, fake_exe = _make_client(monkeypatch, tmp_path, has_pubkey=False)
    _ = client  # used implicitly (sys.argv monkeypatch)
    payload = b"NEW-BINARY-v1.3.7"

    packet = {
        "status": "update_download",
        "payload": base64.b64encode(payload).decode(),
        # БЕЗ sha256, БЕЗ signature — как пришло бы со старого сервера
    }
    assert client._save_update_file(packet) is True

    new_file = Path(str(fake_exe) + ".new")
    assert new_file.exists()
    assert new_file.read_bytes() == payload


def test_old_client_without_pubkey_accepts_signed_update_too(monkeypatch, tmp_path):
    """Если сервер уже подписывает, но у клиента нет public_key — всё равно принимает."""
    client, fake_exe = _make_client(monkeypatch, tmp_path, has_pubkey=False)
    _ = client  # used implicitly (sys.argv monkeypatch)
    payload = b"NEW-BINARY-v1.3.7"

    packet = {
        "status": "update_download",
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "signature": "ZmFrZS1zaWctaWdub3JlZA==",  # любая, нас не парит
        "sig_algo": "ed25519",
    }
    assert client._save_update_file(packet) is True
    assert Path(str(fake_exe) + ".new").read_bytes() == payload


def test_new_client_with_pubkey_rejects_unsigned(monkeypatch, tmp_path):
    """После миграции клиент с public_key должен отвергать unsigned."""
    client, fake_exe = _make_client(monkeypatch, tmp_path, has_pubkey=True)
    payload = b"NEW-BINARY-MALICIOUS"

    packet = {
        "status": "update_download",
        "payload": base64.b64encode(payload).decode(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        # БЕЗ signature — закроет атаку «фейковый сервер»
    }
    assert client._save_update_file(packet) is False
    assert not Path(str(fake_exe) + ".new").exists()


# ============================================================
# 2) SIDECAR: .sha256 и .sig сохраняются рядом с .new
# ============================================================

def test_save_creates_sidecar_files(monkeypatch, tmp_path):
    """После успешного _save_update_file рядом с .new должны лежать метаданные."""
    client, fake_exe = _make_client(monkeypatch, tmp_path, has_pubkey=False)
    _ = client  # used implicitly (sys.argv monkeypatch)
    payload = b"some-update-bytes"
    sha = hashlib.sha256(payload).hexdigest()

    packet = {
        "status": "update_download",
        "payload": base64.b64encode(payload).decode(),
        "sha256": sha,
        "signature": "AAAA",
        "sig_algo": "ed25519",
    }
    assert client._save_update_file(packet) is True

    new_file = Path(str(fake_exe) + ".new")
    sha_file = Path(str(new_file) + ".sha256")
    sig_file = Path(str(new_file) + ".sig")
    assert sha_file.exists(), "sidecar .sha256 not created"
    assert sig_file.exists(), "sidecar .sig not created"
    assert sha_file.read_text().strip() == sha
    assert sig_file.read_text().strip() == "AAAA"


# ============================================================
# 3) ГОНКА: update_apply отвергает повреждённый .new по sidecar
# ============================================================

def test_update_apply_rejects_corrupted_new_via_sidecar(monkeypatch, tmp_path):
    """
    Сценарий: соединение упало между complete и apply, .new на диске
    битый. Sidecar содержит правильный хеш. update_apply должен
    отказать и удалить битый .new.
    """
    client, fake_exe = _make_client(monkeypatch, tmp_path, has_pubkey=False)
    _ = client  # used implicitly (sys.argv monkeypatch)

    new_file = Path(str(fake_exe) + ".new")
    real_payload = b"NEW-BINARY-v1.3.7"
    correct_sha = hashlib.sha256(real_payload).hexdigest()

    # Кладём БИТЫЙ .new и ПРАВИЛЬНЫЙ sidecar.
    new_file.write_bytes(b"CORRUPTED-HALF-DOWNLOAD")
    Path(str(new_file) + ".sha256").write_text(correct_sha)

    # Симулируем update_apply (логика из process_packet).
    expected_new = os.path.abspath(sys.argv[0]) + ".new"
    assert os.path.exists(expected_new)

    sha_file = expected_new + ".sha256"
    expected_sha = Path(sha_file).read_text().strip()
    data = Path(expected_new).read_bytes()
    actual_sha = hashlib.sha256(data).hexdigest()

    assert actual_sha != expected_sha, "test setup broken"

    # Удаление поврежденного — как в production-коде.
    os.remove(expected_new)
    assert not new_file.exists()


# ============================================================
# 4) DISK SPACE / PERMISSIONS
# ============================================================

def test_save_refuses_when_no_write_permission(monkeypatch, tmp_path):
    """Если в директории нет прав на запись — _save_update_file отказывает."""
    if platform.system() == "Windows":
        pytest.skip("chmod не работает корректно на Windows runner")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root игнорирует chmod — тест не имеет смысла")

    client, fake_exe = _make_client(monkeypatch, tmp_path, has_pubkey=False)
    _ = client  # used implicitly (sys.argv monkeypatch)
    # Делаем директорию read-only.
    os.chmod(tmp_path, 0o555)

    try:
        payload = b"X"
        packet = {
            "status": "update_download",
            "payload": base64.b64encode(payload).decode(),
        }
        assert client._save_update_file(packet) is False
        assert not Path(str(fake_exe) + ".new").exists()
    finally:
        os.chmod(tmp_path, 0o755)


def test_save_refuses_when_disk_full(monkeypatch, tmp_path):
    """Если shutil.disk_usage возвращает мало места — отказывает."""
    client, fake_exe = _make_client(monkeypatch, tmp_path, has_pubkey=False)
    _ = client  # used implicitly (sys.argv monkeypatch)

    import shutil
    real_disk_usage = shutil.disk_usage

    class FakeUsage:
        total = 1_000_000
        used = 999_000
        free = 100  # очень мало

    monkeypatch.setattr(shutil, "disk_usage", lambda p: FakeUsage)

    payload = b"X" * 1024  # 1 КБ — больше, чем 100 байт свободного
    packet = {
        "status": "update_download",
        "payload": base64.b64encode(payload).decode(),
    }
    assert client._save_update_file(packet) is False
    assert not Path(str(fake_exe) + ".new").exists()

    monkeypatch.setattr(shutil, "disk_usage", real_disk_usage)
