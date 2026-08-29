"""
tests/test_reconnect.py — Тесты отказоустойчивости при потере связи и авто-переподключения:
- Продолжение теста при отключении сети
- Очередь отложенных результатов при завершении теста офлайн
- Авто-отправка результатов при восстановлении соединения
- Восстановление сессии на сервере по action='reconnect'
- Корректная оценка результатов переподключенного клиента
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

try:
    import PySide6.QtWidgets
    _ = PySide6.QtWidgets
except ImportError:
    pytest.skip("libEGL missing — skipping QtWidgets-dependent tests", allow_module_level=True)

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication
from PySide6.QtNetwork import QAbstractSocket, QTcpSocket

from client.main import StudentClient
from server.main import ConnectedStudent, ExamServer


@pytest.fixture
def app():
    return QCoreApplication.instance() or QCoreApplication(sys.argv)


def test_client_offline_test_continuity(app):
    """Клиент не сбрасывает тест при потере соединения, а входит в режим авто-переподключения."""
    client = StudentClient()
    client._name = "Иванов Иван"
    client._group = "ИСП-311"
    client._host = "127.0.0.1"
    client._port = 9876

    lost_emitted = []
    error_emitted = []
    client.connection_lost.connect(lambda: lost_emitted.append(True))
    client.connection_error.connect(lambda msg: error_emitted.append(msg))

    # Симулируем успешный старт теста
    client._handle_response({
        "status": "success",
        "questions": [{"number": 1, "text": "Вопрос 1", "options": ["A", "B"], "q_type": "single"}],
        "duration": 60,
        "title": "Тест",
        "section": "Часть 1",
        "test_name": "Test1",
    })

    assert client._in_test is True

    # Симулируем обрыв сокета
    client._on_socket_disconnected()

    assert lost_emitted == [True], "Сигнал connection_lost должен быть отправлен"
    assert len(error_emitted) == 0, "connection_error НЕ должен прерывать активный тест"
    assert client._reconnect_timer.isActive(), "Таймер переподключения должен быть запущен"


def test_client_send_result_offline_queues_and_auto_sends(app, monkeypatch):
    """При завершении теста офлайн результат сохраняется в очередь и отправляется при переподключении."""
    client = StudentClient()
    client._name = "Петров Петр"
    client._group = "ИСП-311"
    client._host = "127.0.0.1"
    client._port = 9876
    client._in_test = True

    answers = {1: ["A"], 2: ["B"]}
    sent = client.send_result(answers)

    assert sent is False, "В офлайне результат не отправлен немедленно"
    assert client._pending_results == answers, "Ответы должны сохраниться в очереди"
    assert client._reconnect_timer.isActive(), "Таймер авто-переподключения должен работать"

    # Симулируем успешное восстановление соединения
    sent_packets = []
    monkeypatch.setattr(client._socket, "state", lambda: QAbstractSocket.ConnectedState)
    monkeypatch.setattr(client._socket, "write", lambda data: sent_packets.append(data) or len(data))
    monkeypatch.setattr(client._socket, "flush", lambda: None)

    restored_emitted = []
    client.connection_restored.connect(lambda: restored_emitted.append(True))

    client._on_socket_connected()

    assert restored_emitted == [True]
    assert len(sent_packets) == 1, "Отложенный результат должен быть автоматически отправлен"


def test_server_handle_reconnect(app):
    """Сервер успешно связывает новый сокет с существующей сессией студента."""
    server = ExamServer()
    sock1 = QTcpSocket()
    sock2 = QTcpSocket()

    name = "Сидоров Семён"
    group = "ИСП-311"

    student = ConnectedStudent(sock1, name, group)
    student.questions = [{
        "number": 1,
        "text": "Q1",
        "answers": [{"text": "A", "correct": True}, {"text": "B", "correct": False}],
    }]
    student.exam_start_time = datetime.now()
    server._monitor_data[(name, group)] = student

    written_packets = []
    sock2.write = lambda data: written_packets.append(data)
    sock2.flush = lambda: None

    server._handle_reconnect(sock2, {
        "action": "reconnect",
        "name": name,
        "group": group,
        "version": "1.4.9",
        "os": "linux",
    })

    assert student.socket == sock2
    assert student.active is True
    assert server._students[sock2] == student
    assert len(written_packets) == 1, "Сервер должен подтвердить реконнект"


def test_server_handle_result_from_reconnected_client(app):
    """Сервер принимает результат от переподключенного сокета, используя персональный набор вопросов."""
    server = ExamServer()
    sock = QTcpSocket()

    name = "Козлов Иван"
    group = "ИСП-311"
    group_key = group.lower()

    q1 = {
        "number": 1,
        "text": "Q1",
        "answers": [{"text": "A", "correct": True}, {"text": "B", "correct": False}],
    }
    student = ConnectedStudent(sock, name, group)
    student.questions = [q1]
    student.exam_start_time = datetime.now()
    server._monitor_data[(name, group)] = student

    server._active_exams[group_key] = {
        "duration": 60,
        "questions": [q1],
        "max_attempts": 2,
        "attempts": {name.strip().casefold(): {"count": 0, "exam_start_time": student.exam_start_time}},
    }

    written_packets = []
    sock.write = lambda data: written_packets.append(data)
    sock.flush = lambda: None

    # Отправляем правильный ответ
    server._handle_result(sock, {
        "action": "result",
        "name": name,
        "group": group,
        "answers": {1: ["A"]},
    })

    assert student.finished is True
    assert student.score == "1/1"
    assert len(server._results) == 1
    assert server._results[0]["score"] == "1/1"
