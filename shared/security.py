"""
shared/security.py — подпись и проверка авто-обновлений (Ed25519).

Зачем это нужно
---------------
Авто-обновления TTGTiSO-Test раздаются сервером преподавателя по обычному
TCP-каналу (без TLS). Без криптографической подписи любой компьютер в той
же локальной сети мог бы поднять собственный «сервер» на порту 9876 и
разослать студентам произвольный исполняемый файл — клиент бы его
сохранил и запустил. Это полноценный RCE.

Чтобы это закрыть, мы используем асимметричную подпись Ed25519:

* приватный ключ хранится **только** у преподавателя (вне репозитория),
  им подписывается каждая новая сборка;
* публичный ключ коммитится в репозиторий как `shared/update_public_key.pem`
  и вкомпилируется в клиента;
* клиент сверяет подпись до того, как заменить и запустить новый бинарник.

Если подписи нет или она невалидна — обновление отклоняется, в лог пишется
предупреждение, текущая версия продолжает работать как раньше.

Зависимость: `cryptography` (см. requirements.txt).
"""

from __future__ import annotations

import base64
import hashlib
import os
import sys
from pathlib import Path
from typing import Optional

# ``cryptography`` присутствует в requirements.txt, но если по какой-то
# причине его нет (например, скрипт запущен из срезанной сборки), мы
# деградируем мягко: ``verify_signature`` вернёт False, а сторона сервера
# выбросит RuntimeError при попытке подписать.
try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

    _CRYPTO_AVAILABLE = True
except ImportError:  # pragma: no cover — экзотический рантайм без cryptography
    _CRYPTO_AVAILABLE = False


# ---------------------------------------------------------------------------
# Пути и константы
# ---------------------------------------------------------------------------

PUBLIC_KEY_FILENAME = "update_public_key.pem"


def _candidate_public_key_paths() -> list[Path]:
    """Где искать публичный ключ. Первый существующий файл выигрывает."""
    candidates: list[Path] = []

    # 1) Рядом с этим файлом — для запуска из исходников и для PyInstaller-сборок,
    #    где shared/ копируется как data-файл.
    candidates.append(Path(__file__).resolve().parent / PUBLIC_KEY_FILENAME)

    # 2) Рядом с исполняемым файлом — для Nuitka onefile (распакованная папка).
    if getattr(sys, "frozen", False) or (sys.argv and sys.argv[0]):
        exe_dir = Path(os.path.dirname(os.path.abspath(sys.argv[0])))
        candidates.append(exe_dir / PUBLIC_KEY_FILENAME)

    # 3) PyInstaller _MEIPASS, если кто-то соберёт через него в будущем.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "shared" / PUBLIC_KEY_FILENAME)

    return candidates


def find_public_key_path() -> Optional[Path]:
    """Возвращает путь к публичному ключу или None, если его нигде нет."""
    for p in _candidate_public_key_paths():
        if p.is_file():
            return p
    return None


# ---------------------------------------------------------------------------
# Хэш — используется и для подписи, и для логирования.
# ---------------------------------------------------------------------------


def sha256_hex(data: bytes) -> str:
    """SHA-256 как hex-строка. Удобно показывать в логе/UI."""
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Сторона сервера — подпись
# ---------------------------------------------------------------------------


def load_private_key(pem_path: Path | str) -> "Ed25519PrivateKey":
    """Загружает приватный Ed25519-ключ из PEM-файла."""
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError(
            "Пакет `cryptography` не установлен — установите requirements.txt"
        )
    pem_path = Path(pem_path)
    data = pem_path.read_bytes()
    key = serialization.load_pem_private_key(data, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError(f"{pem_path} не является Ed25519-ключом")
    return key


def sign_bytes(private_key: "Ed25519PrivateKey", payload: bytes) -> str:
    """Подписывает байты и возвращает base64-строку с подписью."""
    if not _CRYPTO_AVAILABLE:
        raise RuntimeError(
            "Пакет `cryptography` не установлен — установите requirements.txt"
        )
    sig = private_key.sign(payload)
    return base64.b64encode(sig).decode("ascii")


def sign_file(private_key: "Ed25519PrivateKey", file_path: Path | str) -> str:
    """Удобный wrapper: прочитать файл и подписать."""
    return sign_bytes(private_key, Path(file_path).read_bytes())


# ---------------------------------------------------------------------------
# Сторона клиента — проверка
# ---------------------------------------------------------------------------


def _load_public_key() -> Optional["Ed25519PublicKey"]:
    """Загружает встроенный публичный ключ, либо None если его нет."""
    if not _CRYPTO_AVAILABLE:
        return None
    path = find_public_key_path()
    if path is None:
        return None
    try:
        key = serialization.load_pem_public_key(path.read_bytes())
    except Exception:  # pragma: no cover — повреждённый ключ
        return None
    if not isinstance(key, Ed25519PublicKey):
        return None
    return key


def verify_signature(payload: bytes, signature_b64: str) -> bool:
    """
    Проверяет подпись. Возвращает True только если:
      * установлен пакет ``cryptography``,
      * найден публичный ключ ``shared/update_public_key.pem``,
      * подпись валидна для переданных байт.

    Любая ошибка превращается в ``False`` — наружу исключения не пробрасываем,
    чтобы клиент мог логировать и спокойно отказаться от обновления.
    """
    if not _CRYPTO_AVAILABLE or not signature_b64:
        return False
    pub = _load_public_key()
    if pub is None:
        return False
    try:
        signature = base64.b64decode(signature_b64, validate=True)
    except Exception:
        return False
    try:
        pub.verify(signature, payload)
        return True
    except InvalidSignature:
        return False
    except Exception:  # pragma: no cover — защитный catch
        return False


def has_public_key() -> bool:
    """Подсказка для UI: «развёрнут ли механизм проверки?»"""
    return _load_public_key() is not None
