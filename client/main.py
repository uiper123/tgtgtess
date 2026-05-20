"""
client/main.py — Точка входа клиента студента.
Сетевая логика (TCP), подключение к серверу, отправка результатов,
шифрованный локальный бэкап.
"""

import sys
import os
import json
import struct
import platform
from datetime import datetime
from typing import Optional, List, Dict, Any

from PySide6.QtCore import Qt, QObject, Signal, Slot, QByteArray, QTimer
from PySide6.QtNetwork import QTcpSocket, QAbstractSocket
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def pack_message(data: dict) -> bytes:
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return struct.pack('!I', len(raw)) + raw


def xor_encrypt(data: bytes, key: bytes = b'EduTestPro2025') -> bytes:
    """Простой XOR-шифр для маскировки локального бэкапа."""
    out = bytearray(len(data))
    klen = len(key)
    for i, b in enumerate(data):
        out[i] = b ^ key[i % klen]
    return bytes(out)


def get_backup_dir() -> str:
    """Возвращает путь к системной директории для скрытого бэкапа."""
    if platform.system() == 'Windows':
        base = os.getenv('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.join(os.path.expanduser('~'), '.config')
    backup_dir = os.path.join(base, 'edutest_system')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir


def save_encrypted_backup(name: str, group: str, score: str, answers: dict):
    """Сохраняет результат в зашифрованном .log файле."""
    data = {
        'name': name,
        'group': group,
        'score': score,
        'answers': answers,
        'timestamp': datetime.now().isoformat(),
    }
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    encrypted = xor_encrypt(raw)

    backup_dir = get_backup_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"session_{ts}.log"
    filepath = os.path.join(backup_dir, filename)

    try:
        with open(filepath, 'wb') as f:
            f.write(encrypted)
    except IOError:
        pass  # Бэкап — не критичен


class StudentClient(QObject):
    """
    TCP-клиент студента.

    Signals:
        connected_ok(list, int)     — вопросы (payload) и длительность (мин)
        connection_error(str)       — ошибка подключения
        result_sent()               — результат успешно отправлен
        log_message(str)
    """

    connected_ok = Signal(list, int, str, str)         # questions, duration, title, section
    connection_error = Signal(str)           # message
    result_sent = Signal(str)                # score calculated by server
    log_message = Signal(str)
    active_group_found = Signal(list)        # active groups

    def __init__(self, parent=None):
        super().__init__(parent)
        self._socket = QTcpSocket(self)
        self._socket.connected.connect(self._on_socket_connected)
        self._socket.readyRead.connect(self._on_data_ready)
        self._socket.errorOccurred.connect(self._on_socket_error)

        self._buffer = QByteArray()
        self._name = ''
        self._group = ''
        self._pending_connect = False
        self._temp_sock = None
        self._temp_buf = QByteArray()

    def check_active_group(self, host: str, port: int):
        """Запрашивает с сервера активные группы без входа."""
        self._temp_sock = QTcpSocket(self)
        self._temp_buf = QByteArray()
        
        def on_connected():
            packet = {'action': 'get_active_group'}
            self._temp_sock.write(pack_message(packet))
            self._temp_sock.flush()
            
        def on_ready_read():
            self._temp_buf.append(self._temp_sock.readAll())
            while len(self._temp_buf) >= 4:
                msg_len = struct.unpack('!I', self._temp_buf[:4].data())[0]
                if len(self._temp_buf) < 4 + msg_len:
                    break
                raw = self._temp_buf[4:4 + msg_len].data().decode('utf-8')
                self._temp_buf = self._temp_buf[4 + msg_len:]
                try:
                    res = json.loads(raw)
                    if res.get('status') == 'success':
                        groups = res.get('groups')
                        if not isinstance(groups, list):
                            group = res.get('group', '')
                            groups = [g.strip() for g in group.split(",") if g.strip()]
                        self.active_group_found.emit([str(g).strip() for g in groups if str(g).strip()])
                    elif res.get('message') == 'exam_not_active':
                        self.active_group_found.emit([])
                except Exception:
                    pass
                self._temp_sock.disconnectFromHost()

        self._temp_sock.connected.connect(on_connected)
        self._temp_sock.readyRead.connect(on_ready_read)
        self._temp_sock.errorOccurred.connect(lambda error: self.active_group_found.emit([]))
        self._temp_sock.connectToHost(host.strip(), port)

    def connect_to_server(self, host: str, port: int, name: str, group: str):
        self._name = name.strip()
        self._group = group.strip()
        self._pending_connect = True
        self._buffer.clear()
        self._socket.connectToHost(host.strip(), port)

    @Slot()
    def _on_socket_connected(self):
        if self._pending_connect:
            self._pending_connect = False
            packet = {
                'action': 'connect',
                'name': self._name,
                'group': self._group,
            }
            self._socket.write(pack_message(packet))
            self._socket.flush()

    @Slot()
    def _on_data_ready(self):
        self._buffer.append(self._socket.readAll())

        while len(self._buffer) >= 4:
            msg_len = struct.unpack('!I', self._buffer[:4].data())[0]
            if len(self._buffer) < 4 + msg_len:
                break
            raw = self._buffer[4:4 + msg_len].data().decode('utf-8')
            self._buffer = self._buffer[4 + msg_len:]
            try:
                packet = json.loads(raw)
            except json.JSONDecodeError:
                continue
            self._handle_response(packet)

    def _handle_response(self, packet: dict):
        status = packet.get('status')
        if status == 'success':
            questions = packet.get('questions', [])
            duration = packet.get('duration', 60)
            title = packet.get('title', 'Итоговое тестирование')
            section = packet.get('section', 'Раздел: Основная часть')
            self.connected_ok.emit(questions, duration, title, section)
        elif status == 'result_confirmed':
            score = packet.get('score', '0/0')
            self.result_sent.emit(score)
        elif status == 'error':
            msg = packet.get('message', 'unknown')
            if msg == 'wrong_group':
                self.connection_error.emit(
                    'Вы не числитесь в текущей группе тестирования'
                )
            elif msg == 'exam_not_active':
                self.connection_error.emit('Экзамен ещё не запущен')
            elif msg == 'empty_fields':
                self.connection_error.emit('Заполните все поля')
            elif msg == 'attempts_exceeded':
                self.connection_error.emit('Лимит попыток для этого теста исчерпан')
            elif msg == 'duplicate_connection':
                self.connection_error.emit('Этот студент уже проходит тест')
            else:
                self.connection_error.emit(f'Ошибка сервера: {msg}')

    @Slot(QAbstractSocket.SocketError)
    def _on_socket_error(self, error):
        self.connection_error.emit(
            f'Не удалось подключиться к серверу: {self._socket.errorString()}'
        )

    def send_result(self, answers: dict):
        """Отправляет ответы на сервер для точного расчёта."""
        packet = {
            'action': 'result',
            'name': self._name,
            'group': self._group,
            'answers': answers,
        }
        if self._socket.state() == QAbstractSocket.ConnectedState:
            self._socket.write(pack_message(packet))
            self._socket.flush()

        # Шифрованный бэкап
        score_placeholder = f"{len(answers)}"
        save_encrypted_backup(self._name, self._group, score_placeholder, answers)

    def disconnect(self):
        if self._socket.state() == QAbstractSocket.ConnectedState:
            self._socket.disconnectFromHost()

    @property
    def student_name(self) -> str:
        return self._name

    @property
    def student_group(self) -> str:
        return self._group


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TTGTiSO-Test — Студент")
    app.setOrganizationName("EduTest")

    client = StudentClient()

    from ui_client import StudentWindow
    window = StudentWindow(client)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
