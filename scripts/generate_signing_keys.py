#!/usr/bin/env python3
"""
scripts/generate_signing_keys.py — генерирует пару ключей Ed25519
для подписи авто-обновлений EduTest Pro.

Запуск:
    python scripts/generate_signing_keys.py

После выполнения:
    * shared/update_public_key.pem  — добавьте в репозиторий (он не секретный).
    * update_private_key.pem        — НЕ коммитьте, держите в безопасном месте
                                       (например, в ~/.edutest/, chmod 600).

Скрипт никогда не перезаписывает существующие ключи без --force —
случайно потерять приватный ключ значит сделать все будущие обновления
невозможными до перевыпуска публичного ключа.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Чтобы запускать прямо из репозитория.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public",
        default=str(Path(__file__).resolve().parents[1] / "shared" / "update_public_key.pem"),
        help="Куда положить публичный ключ (по умолчанию shared/update_public_key.pem)",
    )
    parser.add_argument(
        "--private",
        default="update_private_key.pem",
        help="Куда положить приватный ключ (по умолчанию ./update_private_key.pem)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Перезаписать существующие файлы (опасно — потеря приватного ключа).",
    )
    args = parser.parse_args()

    pub_path = Path(args.public)
    priv_path = Path(args.private)

    for p in (pub_path, priv_path):
        if p.exists() and not args.force:
            print(f"❌ {p} уже существует. Используйте --force, чтобы перезаписать.", file=sys.stderr)
            return 2

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

    pub_path.parent.mkdir(parents=True, exist_ok=True)
    pub_path.write_bytes(pub_pem)

    priv_path.parent.mkdir(parents=True, exist_ok=True)
    priv_path.write_bytes(priv_pem)
    try:
        # Ограничиваем доступ к приватному ключу — read/write только владельцу.
        os.chmod(priv_path, 0o600)
    except OSError:
        # На Windows chmod может игнорироваться — это нормально.
        pass

    print(f"✅ Публичный ключ:  {pub_path}")
    print(f"✅ Приватный ключ:  {priv_path}  (chmod 600)")
    print()
    print("Следующие шаги:")
    print(f"  1. git add {pub_path}")
    print(f"  2. Переложите {priv_path} в надёжное место (НЕ коммитить!)")
    print("  3. Подписывайте сборки: python scripts/sign_update.py <бинарник>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
