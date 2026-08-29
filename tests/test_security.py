"""Тесты на shared.security — подпись Ed25519 для авто-обновлений."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

cryptography = pytest.importorskip("cryptography")

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from shared import security


@pytest.fixture
def keypair(tmp_path: Path, monkeypatch):
    """
    Генерирует свежую пару ключей и подкладывает публичный туда, где его
    найдёт `_load_public_key`. Никакого глобального state — каждый тест
    изолирован.
    """
    key = Ed25519PrivateKey.generate()
    pub_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    priv_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    priv_path = tmp_path / "priv.pem"
    pub_path = tmp_path / security.PUBLIC_KEY_FILENAME
    priv_path.write_bytes(priv_pem)
    pub_path.write_bytes(pub_pem)

    monkeypatch.setattr(
        security, "_candidate_public_key_paths", lambda: [pub_path]
    )
    return key, priv_path, pub_path


def test_signature_round_trip(keypair):
    _, priv_path, _ = keypair
    payload = b"binary blob v1"
    pk = security.load_private_key(priv_path)
    sig = security.sign_bytes(pk, payload)
    assert security.verify_signature(payload, sig) is True


def test_signature_rejected_when_payload_tampered(keypair):
    _, priv_path, _ = keypair
    pk = security.load_private_key(priv_path)
    sig = security.sign_bytes(pk, b"original")
    assert security.verify_signature(b"tampered", sig) is False


def test_signature_rejected_when_signature_garbage(keypair):
    payload = b"x"
    bogus = base64.b64encode(b"definitely not a signature").decode()
    assert security.verify_signature(payload, bogus) is False


def test_verify_returns_false_when_no_public_key(monkeypatch):
    monkeypatch.setattr(security, "_candidate_public_key_paths", lambda: [])
    assert security.has_public_key() is False
    assert security.verify_signature(b"x", "AAAA") is False


def test_empty_signature_returns_false(keypair):
    assert security.verify_signature(b"x", "") is False


def test_sha256_hex():
    # echo -n hello | sha256sum
    assert (
        security.sha256_hex(b"hello")
        == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    )


def test_key_generation_and_saving(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(security, "_shared_public_key_path", lambda: tmp_path / "shared_pub.pem")

    # Временно перенаправляем пути поиска публичного ключа только на локальный путь
    local_pub_path = tmp_path / ".edutest" / security.PUBLIC_KEY_FILENAME
    monkeypatch.setattr(security, "_candidate_public_key_paths", lambda: [local_pub_path])

    # Убеждаемся, что локального ключа изначально нет
    assert security.has_locally_saved_key() is False
    assert security.get_public_key_pem() is None

    # Генерируем новую пару ключей
    priv_path, pub_path = security.generate_and_save_keys()

    assert priv_path.exists()
    assert pub_path.exists()
    assert security.has_locally_saved_key() is True

    pub_pem = security.get_public_key_pem()
    assert pub_pem is not None
    assert "-----BEGIN PUBLIC KEY-----" in pub_pem

    # Тестируем ручное сохранение публичного ключа
    assert security.save_public_key("dummy public key content") is True
    assert (tmp_path / ".edutest" / security.PUBLIC_KEY_FILENAME).read_text() == "dummy public key content\n"
