#!/usr/bin/env python3
"""
scripts/sign_update.py — подписывает бинарник обновления приватным
Ed25519-ключом и кладёт рядом файл `<бинарник>.sig` с base64-подписью.

Запуск:
    python scripts/sign_update.py dist/student/TTGTiSO-Test-student.exe
    python scripts/sign_update.py dist/student/TTGTiSO-Test-student \
        --key ~/.edutest/update_private_key.pem

По умолчанию ищет приватный ключ в (по порядку):
    1. путь, указанный через --key
    2. переменную окружения EDUTEST_PRIVATE_KEY
    3. ./update_private_key.pem
    4. ~/.edutest/update_private_key.pem
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.security import load_private_key, sha256_hex, sign_file


def _find_private_key(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("EDUTEST_PRIVATE_KEY")
    if env:
        return Path(env).expanduser()
    for p in (
        Path("update_private_key.pem"),
        Path.home() / ".edutest" / "update_private_key.pem",
    ):
        if p.is_file():
            return p
    raise FileNotFoundError(
        "Приватный ключ не найден. Передайте --key, либо создайте "
        "update_private_key.pem через scripts/generate_signing_keys.py."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", help="Путь к собранному бинарнику обновления")
    parser.add_argument("--key", help="Путь к приватному ключу (PEM)")
    parser.add_argument("--out", help="Куда записать .sig (по умолчанию <binary>.sig)")
    args = parser.parse_args()

    binary = Path(args.binary)
    if not binary.is_file():
        print(f"❌ Файл {binary} не найден", file=sys.stderr)
        return 2

    key_path = _find_private_key(args.key)
    private_key = load_private_key(key_path)
    signature_b64 = sign_file(private_key, binary)
    digest = sha256_hex(binary.read_bytes())

    out_path = Path(args.out) if args.out else binary.with_suffix(binary.suffix + ".sig")
    out_path.write_text(signature_b64 + "\n", encoding="utf-8")

    print(f"✅ Подпись:     {out_path}")
    print(f"   ключ:       {key_path}")
    print(f"   sha256:     {digest}")
    print(f"   размер:     {binary.stat().st_size:,} байт")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
