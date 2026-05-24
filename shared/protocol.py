import json
import struct

def pack_message(data: dict) -> bytes:
    """Упаковывает словарь в сетевой пакет: [4 байта длины][JSON UTF-8]."""
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return struct.pack('!I', len(raw)) + raw
