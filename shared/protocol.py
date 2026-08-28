import json
import struct

DISCOVERY_PORT = 9877
DISCOVERY_MAGIC = "TTGTISO_DISCOVERY"
DISCOVERY_BEACON_INTERVAL_MS = 2000


def pack_message(data: dict) -> bytes:
    """Упаковывает словарь в сетевой пакет: [4 байта длины][JSON UTF-8]."""
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return struct.pack('!I', len(raw)) + raw
