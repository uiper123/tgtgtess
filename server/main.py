"""
server/main.py — Точка входа сервера преподавателя (TCP-сервер + GUI).

Запускает PySide6-приложение с интерфейсом преподавателя.
TCP-сервер работает через QTcpServer, принимая JSON-пакеты от студентов.
"""

import csv
import json
import os
import random
import struct
import sys
from datetime import datetime
from functools import partial
from typing import Any, Dict, List, Optional

# Обеспечиваем гарантированное обнаружение certifi сборщиком Nuitka/PyInstaller
try:
    import certifi
except ImportError:
    certifi = None

from PySide6.QtCore import QByteArray, QObject, Signal, Slot
from PySide6.QtNetwork import QHostAddress, QTcpServer, QTcpSocket
from PySide6.QtWidgets import QApplication

# Добавляем корень проекта в sys.path для импорта shared
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.parser import calculate_score, parse_test_file, questions_to_network_payload
from shared.protocol import pack_message
from shared.security import load_private_key, sha256_hex, sign_bytes
from shared.version import GITHUB_REPO, VERSION

try:
    from .storage import project_root, results_path, safe_test_filename
except ImportError:
    from storage import project_root, results_path, safe_test_filename


def _verified_ssl_context():
    """
    Возвращает SSL-контекст для urllib, который **всегда** проверяет
    сертификаты. До 1.3.7 здесь использовался ``ssl._create_unverified_context``,
    что отключало TLS-проверку при обращении к GitHub API и оставляло
    дверь открытой для MITM. Теперь:
      1) пытаемся использовать корневой store из пакета ``certifi`` —
         это надёжно работает и на «голом» Windows без обновлённых
         системных сертификатов;
      2) если ``certifi`` нет — берём дефолтный системный контекст;
         он тоже проверяет, просто полагается на то, что в ОС не сломан
         CA-bundle.
    """
    import ssl
    try:
        import certifi
        ca_path = certifi.where()
        if os.path.exists(ca_path):
            return ssl.create_default_context(cafile=ca_path)
    except Exception:
        pass

    ctx = ssl.create_default_context()
    try:
        ctx.load_default_certs()
    except Exception:
        pass
    return ctx


# ---------------------------------------------------------------------------

MAX_MESSAGE_SIZE = 64 * 1024 * 1024  # 64 МБ. До 1.3.7 было 500 МБ — это открывало
                                     # дверь DoS-атакам (memory exhaustion) на сервер
                                     # и клиент. Реальные тесты и обновления влезают.
UPDATE_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB бинарных данных на чанк
OLD_CLIENT_MAX_SIZE = 45 * 1024 * 1024  # Лимит для старых клиентов (< v1.3.5)


def _version_tuple(v: str) -> tuple:
    """Преобразует строку версии '1.3.3' в кортеж (1, 3, 3) для сравнения."""
    try:
        return tuple(int(x) for x in v.split('.'))
    except (ValueError, AttributeError):
        return (0, 0, 0)


class ConnectedStudent:
    """Данные о подключённом студенте."""
    __slots__ = ('active', 'answers', 'buffer', 'cheat_warnings', 'connect_time', 'exam_start_time', 'finished', 'group', 'name', 'os', 'questions', 'score', 'socket', 'version')

    def __init__(self, socket: QTcpSocket, name: str, group: str):
        self.socket = socket
        self.name = name
        self.group = group
        self.buffer = QByteArray()
        self.finished = False
        self.score: Optional[str] = None
        self.active = True
        self.answers: Dict[int, List[str]] = {}
        self.questions: List[Dict[str, Any]] = []
        self.cheat_warnings = []
        self.connect_time = datetime.now()
        self.version = "0.0.0"
        self.os = "windows"
        self.exam_start_time = None


class ExamServer(QObject):
    """
    TCP-сервер экзаменационного тестирования.

    Signals:
        student_connected(str, str)   — ФИО и группа подключившегося студента
        student_finished(str, str, str) — ФИО, группа и оценка завершившего
        server_started(str, int)      — адрес и порт запущенного сервера
        server_error(str)             — сообщение об ошибке
        log_message(str)              — произвольное лог-сообщение
    """

    student_connected = Signal(str, str)          # name, group
    student_finished = Signal(str, str, str)       # name, group, score
    student_disconnected = Signal(str, str)       # name, group
    student_cheat_warning = Signal(str, str, str)  # name, group, description
    server_started = Signal(str, int)              # address, port
    server_error = Signal(str)                     # message
    log_message = Signal(str)                      # message

    DEFAULT_PORT = 9876

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tcp_server = QTcpServer(self)
        self._tcp_server.newConnection.connect(self._on_new_connection)

        # Считываем сохраненный порт из QSettings на старте приложения
        from PySide6.QtCore import QSettings
        settings = QSettings("EduTest", "Server")
        self.DEFAULT_PORT = settings.value("tcp_port", 9876, type=int)

        # Текущие настройки экзамена
        self._allowed_group: str = ''
        self._duration_minutes: int = 60
        self._questions: List[Dict[str, Any]] = []     # полные вопросы (с correct)
        self._network_payload: List[Dict[str, Any]] = []  # вопросы для отправки студентам
        self._exam_active: bool = False

        # Несколько запущенных экзаменов одновременно
        self._active_exams: Dict[str, Dict[str, Any]] = {}

        # Кастомные заголовки теста для студентов
        self.test_title: str = "Итоговое тестирование"
        self.test_section: str = "Раздел: Основная часть"

        # Подключённые студенты: socket -> ConnectedStudent
        self._students: Dict[QTcpSocket, ConnectedStudent] = {}
        self._pending_buffers: Dict[QTcpSocket, QByteArray] = {}

        # Все студенты, подключившиеся за время экзамена: (name, group) -> ConnectedStudent
        self._monitor_data: Dict[tuple, ConnectedStudent] = {}

        # Результаты текущего экзамена
        self._results: List[Dict[str, str]] = []

        # Все исторические результаты (персистентные)
        self._all_results: List[Dict[str, Any]] = []
        self._load_all_results_from_file()

    def _ensure_signing_keys(self):
        """Проверяет наличие ключей подписи и генерирует их при отсутствии."""
        try:
            key_candidates = []
            env_key = os.environ.get("EDUTEST_PRIVATE_KEY")
            if env_key:
                key_candidates.append(env_key)
            key_candidates.append(os.path.expanduser("~/.edutest/update_private_key.pem"))

            has_key = False
            for kp in key_candidates:
                if os.path.isfile(kp):
                    has_key = True
                    break

            if not has_key:
                self.log_message.emit("⚠️ Приватный ключ подписи не найден. Автоматическая генерация новой пары ключей...")
                from shared.security import generate_and_save_keys
                priv_path, pub_path = generate_and_save_keys()
                self.log_message.emit(f"✅ Успешно сгенерирована новая пара ключей.")
                self.log_message.emit(f"   Приватный: {priv_path}")
                self.log_message.emit(f"   Публичный: {pub_path}")
        except Exception as e:
            self.log_message.emit(f"❌ Не удалось автоматически сгенерировать ключи подписи: {e}")

    def start_background_listening(self, port=None):
        """Запускает прослушивание порта сервером для фоновых дежурных подключений."""
        self._ensure_signing_keys()

        if port is None:
            port = self.DEFAULT_PORT

        if not self._tcp_server.isListening():
            from PySide6.QtNetwork import QHostAddress
            if self._tcp_server.listen(QHostAddress.AnyIPv4, port):
                self.log_message.emit(f"Сервер переведен в режим ожидания на порту {port}")
                # Вызываем сигнал запуска, чтобы обновился GUI
                addr = self._tcp_server.serverAddress().toString()
                self.server_started.emit(addr, port)
            else:
                self.server_error.emit(
                    f"Не удалось запустить дежурный сервер на порту {port}: "
                    f"{self._tcp_server.errorString()}"
                )

    # -- Публичные методы управления экзаменом --

    def load_test(self, filepath: str) -> int:
        """
        Загружает файл теста, парсит вопросы.
        Возвращает количество загруженных вопросов.
        """
        parsed = parse_test_file(filepath)
        self._questions = parsed
        self.test_title = getattr(parsed, "title", "Итоговое тестирование")
        self.test_section = getattr(parsed, "section", "Раздел: Основная часть")
        self._network_payload = questions_to_network_payload(self._questions)
        count = len(self._questions)
        self.log_message.emit(f"Загружен тест: {os.path.basename(filepath)} ({count} вопросов)")
        return count

    def start_exam(self, group: str, duration: int, questions: list, title: str, section: str, test_name: str, port: int = None, partial_multiple: bool = True, random_order: bool = False, max_attempts: int = 1, questions_limit: int = None, cheat_warning_limit: int = 3, shuffle_answers: bool = False):
        """Запускает экзамен для конкретной группы: открывает TCP-порт и добавляет в список активных."""
        if not questions:
            self.server_error.emit("Сначала загрузите или выберите файл теста!")
            return

        group_key = group.strip().lower()
        self._active_exams[group_key] = {
            'group': group.strip(),
            'test_name': test_name,
            'questions': questions,
            'network_payload': questions_to_network_payload(questions, shuffle_answers=shuffle_answers),
            'duration': duration,
            'title': title,
            'section': section,
            'partial_multiple': partial_multiple,
            'random_order': random_order,
            'shuffle_answers': shuffle_answers,
            'max_attempts': max(1, int(max_attempts)),
            'attempts': {},
            'questions_limit': questions_limit,
            'cheat_warning_limit': cheat_warning_limit,
        }

        self._allowed_group = group.strip()
        self._duration_minutes = duration

        if port is None:
            port = self.DEFAULT_PORT

        if not self._tcp_server.isListening():
            if not self._tcp_server.listen(QHostAddress.AnyIPv4, port):
                self.server_error.emit(
                    f"Не удалось запустить сервер на порту {port}: "
                    f"{self._tcp_server.errorString()}"
                )
                self._active_exams.pop(group_key, None)
                return

        self._exam_active = True
        addr = self._tcp_server.serverAddress().toString()
        self.server_started.emit(addr, port)
        self.log_message.emit(
            f"Экзамен запущен — группа: {group.strip()}, тест: {test_name}, "
            f"время: {duration} мин, порт: {port}"
        )

    def stop_exam_for_group(self, group: str):
        """Останавливает экзамен для конкретной группы и отключает её студентов."""
        group_key = group.strip().lower()
        if group_key in self._active_exams:
            exam = self._active_exams.pop(group_key)
            # Отключаем студентов только этой группы
            for sock, student in list(self._students.items()):
                if student.group.strip().lower() == group_key:
                    try:
                        sock.write(pack_message({"status": "force_stopped"}))
                        sock.flush()
                    except Exception:
                        pass
                    sock.disconnectFromHost()
                    self._students.pop(sock, None)

            self.log_message.emit(f"Экзамен для группы '{exam['group']}' остановлен.")

        # Если активных экзаменов больше нет, переводим в дежурный режим ожидания
        if not self._active_exams:
            self._exam_active = False
            self.log_message.emit("Все экзамены остановлены. Сервер переведен в дежурный режим ожидания.")
            self._export_results_csv()

    def stop_exam(self):
        """Останавливает все экзамены."""
        self._exam_active = False
        self._active_exams.clear()
        for sock in list(self._students.keys()):
            try:
                sock.write(pack_message({"status": "force_stopped"}))
                sock.flush()
            except Exception:
                pass
            sock.disconnectFromHost()
        self._students.clear()
        self.log_message.emit("Все экзамены остановлены. Сервер переведен в дежурный режим ожидания.")
        self._export_results_csv()

    @property
    def is_active(self) -> bool:
        return self._exam_active

    @property
    def connected_students_count(self) -> int:
        return len(self._students)

    @property
    def finished_students_count(self) -> int:
        return sum(1 for s in self._students.values() if s.finished)

    @property
    def results(self) -> List[Dict[str, Any]]:
        return list(self._all_results)

    @property
    def questions_count(self) -> int:
        return len(self._questions)

    @property
    def questions(self) -> List[Dict[str, Any]]:
        return self._questions

    def get_active_exams(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._active_exams)

    # ---------- Helpers for `attempts` dict ----------
    # Исторически attempts[student_key] хранил просто int (число использованных
    # попыток). Чтобы починить читерство через переподключение, нам нужно ещё
    # хранить exam_start_time. Делаем структуру dict, но читаем обе формы.

    @staticmethod
    def _attempt_record(exam: dict, student_key: str) -> dict:
        """Возвращает (создавая если нужно) запись попыток как dict."""
        attempts = exam.setdefault('attempts', {})
        rec = attempts.get(student_key)
        if isinstance(rec, int):
            # Миграция из старого int-формата.
            rec = {'count': rec, 'exam_start_time': None}
            attempts[student_key] = rec
        elif rec is None:
            rec = {'count': 0, 'exam_start_time': None}
            attempts[student_key] = rec
        return rec

    @classmethod
    def _attempt_count(cls, exam: dict, student_key: str) -> int:
        return cls._attempt_record(exam, student_key).get('count', 0)

    @classmethod
    def _attempt_inc(cls, exam: dict, student_key: str) -> int:
        rec = cls._attempt_record(exam, student_key)
        rec['count'] = rec.get('count', 0) + 1
        return rec['count']

    @classmethod
    def _attempt_get_or_init_start_time(cls, exam: dict, student_key: str) -> datetime:
        """Возвращает exam_start_time текущей попытки. Если он не был задан —
        ставит datetime.now() и возвращает. Это и есть якорь, который не
        сбрасывается при переподключении."""
        rec = cls._attempt_record(exam, student_key)
        start = rec.get('exam_start_time')
        if isinstance(start, datetime):
            return start
        if isinstance(start, str):
            try:
                parsed = datetime.fromisoformat(start)
                rec['exam_start_time'] = parsed
                return parsed
            except ValueError:
                pass
        now = datetime.now()
        rec['exam_start_time'] = now
        return now

    @classmethod
    def _attempt_reset_start_time(cls, exam: dict, student_key: str):
        """Сбрасывает якорь — вызывается только когда попытка реально закрыта
        (либо студент сдал, либо force_stop, либо лимит времени превышен)."""
        rec = cls._attempt_record(exam, student_key)
        rec['exam_start_time'] = None


    def get_connected_students(self) -> List[ConnectedStudent]:
        return list(self._students.values())

    # -- Внутренние обработчики сетевых событий --

    @Slot()
    def _on_new_connection(self):
        while self._tcp_server.hasPendingConnections():
            client_socket = self._tcp_server.nextPendingConnection()
            if client_socket is None:
                continue
            self._pending_buffers[client_socket] = QByteArray()
            client_socket.readyRead.connect(partial(self._on_data_ready, client_socket))
            client_socket.disconnected.connect(partial(self._on_disconnected, client_socket))

    def _on_data_ready(self, sock: QTcpSocket):
        """Читает данные из сокета и обрабатывает JSON-пакеты."""
        student = self._students.get(sock)
        buf = student.buffer if student is not None else self._pending_buffers.setdefault(sock, QByteArray())
        buf.append(sock.readAll())

        while len(buf) >= 4:
            msg_len = struct.unpack('!I', buf[:4].data())[0]
            if msg_len > MAX_MESSAGE_SIZE:
                self.log_message.emit(f"Пакет клиента превышает допустимый размер: {msg_len} байт")
                self._pending_buffers.pop(sock, None)
                sock.disconnectFromHost()
                return
            if len(buf) < 4 + msg_len:
                break

            raw_payload = buf[4:4 + msg_len].data()
            buf = buf[4 + msg_len:]

            try:
                packet = json.loads(raw_payload.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                self.log_message.emit(f"Ошибка JSON от клиента: {exc}")
                continue

            self._handle_packet(sock, packet)

        current_student = self._students.get(sock)
        if current_student is not None:
            current_student.buffer = buf
            self._pending_buffers.pop(sock, None)
        else:
            self._pending_buffers[sock] = buf

    def _handle_packet(self, sock: QTcpSocket, packet: dict):
        """Обрабатывает один JSON-пакет от клиента."""
        action = packet.get('action')

        if action == 'connect':
            self._handle_connect(sock, packet)
        elif action == 'result':
            self._handle_result(sock, packet)
        elif action == 'get_active_group':
            self._handle_get_active_group(sock, packet)
        elif action == 'get_attempts_left':
            self._handle_get_attempts_left(sock, packet)
        elif action == 'cheat_warning':
            self._handle_cheat_warning(sock, packet)
        else:
            self.log_message.emit(f"Неизвестное действие: {action}")

    def _handle_cheat_warning(self, sock: QTcpSocket, packet: dict):
        """Обрабатывает пакет с предупреждением о нарушении правил прохождения теста."""
        name = packet.get('name', 'Неизвестный')
        group = packet.get('group', 'Неизвестная')
        desc = packet.get('description', 'Попытка переключения рабочего стола/окна')

        self.log_message.emit(f"⚠️ ВНИМАНИЕ: Студент {name} ({group}) нарушил режим тестирования: {desc}")

        student_key = (name, group)
        if student_key in self._monitor_data:
            student = self._monitor_data[student_key]
            if not hasattr(student, 'cheat_warnings') or student.cheat_warnings is None:
                student.cheat_warnings = []
            student.cheat_warnings.append(desc)

        self.student_cheat_warning.emit(name, group, desc)

    def _handle_get_active_group(self, sock: QTcpSocket, packet: dict):
        """Отправляет список активных групп."""
        if not self._exam_active or not self._active_exams:
            response = {'status': 'error', 'message': 'exam_not_active'}
        else:
            groups = [exam['group'] for exam in self._active_exams.values()]
            response = {
                'status': 'success',
                'groups': groups,
                'group': ", ".join(groups),  # Совместимость со старым клиентом.
            }
        sock.write(pack_message(response))
        sock.flush()

    def _handle_get_attempts_left(self, sock: QTcpSocket, packet: dict):
        """Отправляет количество оставшихся попыток студента."""
        name = packet.get('name', '').strip()
        group = packet.get('group', '').strip()

        attempts_left = 0
        max_attempts = 0

        if name and group:
            group_key = group.lower()
            if self._exam_active and group_key in self._active_exams:
                exam = self._active_exams[group_key]
                student_key = name.strip().casefold()
                attempts_used = self._attempt_count(exam, student_key)
                max_attempts = exam.get('max_attempts', 1)
                attempts_left = max(0, max_attempts - attempts_used)

        response = {
            'status': 'attempts_left',
            'attempts_left': attempts_left,
            'max_attempts': max_attempts
        }
        sock.write(pack_message(response))
        sock.flush()

    def _handle_connect(self, sock: QTcpSocket, packet: dict):
        """Обрабатывает запрос студента на подключение."""
        name = packet.get('name', '').strip()
        group = packet.get('group', '').strip()
        client_version = packet.get('version', '0.0.0')
        client_os = packet.get('os', 'unknown')

        # Проверка обновлений для клиента
        upd_dir = self.get_updates_dir()
        if os.path.exists(upd_dir):
            # Ищем файл для соответствующей ОС (например, .exe для windows)
            upd_file = None
            if client_os == 'windows':
                for f in os.listdir(upd_dir):
                    if f.lower().endswith('.exe'):
                        upd_file = os.path.join(upd_dir, f)
                        break
            else:
                for f in os.listdir(upd_dir):
                    if 'student' in f.lower() and not f.lower().endswith('.exe'):
                        upd_file = os.path.join(upd_dir, f)
                        break

            if upd_file and client_version != VERSION:
                try:
                    client_ver = _version_tuple(client_version)
                    sent = self.send_update_to_socket(
                        sock, upd_file, name, client_os,
                        version_tag="",
                        client_version=client_ver,
                        progress_cb=None,
                    )
                    if sent:
                        return
                except Exception as e:
                    self.log_message.emit(f"Ошибка при чтении файла обновления: {e}")

        # Если имя или группа пустые, регистрируем клиента как "Ожидание" (Idle/Waiting)
        if not name or not group:
            peer_ip = sock.peerAddress().toString().removeprefix("::ffff:")
            display_name = name if name else f"Устройство {peer_ip}"
            display_group = group if group else "Ожидание"

            student = ConnectedStudent(sock, display_name, display_group)
            student.version = client_version
            student.os = client_os
            student.active = False
            self._students[sock] = student
            self.student_connected.emit(display_name, display_group)
            self.log_message.emit(f"Фоновое дежурное подключение: {display_name} ({client_os}, версия {client_version})")

            # Отправляем подтверждение idle-подключения
            response = {'status': 'idle_connected', 'version': VERSION}
            from shared.security import get_public_key_pem
            pub_key = get_public_key_pem()
            if pub_key:
                response['public_key'] = pub_key
            sock.write(pack_message(response))
            sock.flush()
            return

        group_key = group.lower()

        # Проверка группы
        if not self._exam_active or group_key not in self._active_exams:
            response = {'status': 'error', 'message': 'wrong_group'}
            sock.write(pack_message(response))
            sock.flush()
            self.log_message.emit(
                f"Отклонён: {name} (группа '{group}' не допущена или экзамен не активен)"
            )
            return

        exam = self._active_exams[group_key]
        student_key = name.strip().casefold()
        attempts_used = self._attempt_count(exam, student_key)
        max_attempts = exam.get('max_attempts', 1)
        if attempts_used >= max_attempts:
            response = {'status': 'error', 'message': 'attempts_exceeded'}
            sock.write(pack_message(response))
            sock.flush()
            self.log_message.emit(
                f"Отклонён: {name} ({group}) — лимит попыток исчерпан ({attempts_used}/{max_attempts})"
            )
            return

        for existing in self._students.values():
            if (
                existing.active
                and not existing.finished
                and existing.group.strip().lower() == group_key
                and existing.name.strip().casefold() == student_key
            ):
                response = {'status': 'error', 'message': 'duplicate_connection'}
                sock.write(pack_message(response))
                sock.flush()
                self.log_message.emit(f"Отклонён: {name} ({group}) — уже есть активная попытка")
                return

        # Регистрируем студента
        student = ConnectedStudent(sock, name, group)
        student.version = client_version
        student.os = client_os
        self._students[sock] = student
        self._monitor_data[(name, group)] = student

        questions_for_student = list(exam['questions'])
        limit = exam.get('questions_limit')
        if limit and limit < len(questions_for_student):
            questions_for_student = random.sample(questions_for_student, limit)
        elif exam.get('random_order'):
            questions_for_student = random.sample(questions_for_student, len(questions_for_student))

        student.questions = questions_for_student

        # Якорь времени экзамена для конкретной (group, name, attempt).
        # При первом подключении ставится datetime.now(); при ре-коннекте —
        # достаётся то же самое значение. Это закрывает читерство через
        # отключение Wi-Fi для сброса таймера (см. SECURITY.md, R-1).
        student.exam_start_time = self._attempt_get_or_init_start_time(exam, student_key)
        elapsed = (datetime.now() - student.exam_start_time).total_seconds()
        total_seconds = exam['duration'] * 60
        remaining_seconds = max(0, int(total_seconds - elapsed))

        # Отправляем тест
        response = {
            'status': 'success',
            'questions': questions_to_network_payload(questions_for_student, shuffle_answers=exam.get('shuffle_answers', False)),
            'duration': exam['duration'],
            'remaining_seconds': remaining_seconds,
            'exam_start_time': student.exam_start_time.isoformat(),
            'title': exam['title'],
            'section': exam['section'],
            'test_name': exam.get('test_name', 'Тест'),
            'cheat_warning_limit': exam.get('cheat_warning_limit', 3),
        }
        from shared.security import get_public_key_pem
        pub_key = get_public_key_pem()
        if pub_key:
            response['public_key'] = pub_key
        sock.write(pack_message(response))
        sock.flush()

        self.student_connected.emit(name, group)
        self.log_message.emit(f"Подключён: {name} ({group})")

    def _handle_result(self, sock: QTcpSocket, packet: dict):
        """Обрабатывает отправку результатов от студента."""
        student = self._students.get(sock)
        if student is None:
            sock.write(pack_message({'status': 'error', 'message': 'not_connected'}))
            sock.flush()
            self.log_message.emit("Отклонён результат от неподключённого клиента")
            return

        if student.finished:
            sock.write(pack_message({'status': 'result_confirmed', 'score': student.score or '0/0'}))
            sock.flush()
            self.log_message.emit(f"Повторный результат проигнорирован: {student.name} ({student.group})")
            return

        name = student.name
        group = student.group
        answers = packet.get('answers', {})
        if not isinstance(answers, dict):
            sock.write(pack_message({'status': 'error', 'message': 'invalid_answers'}))
            sock.flush()
            return

        int_answers = {}
        for k, v in answers.items():
            try:
                int_answers[int(k)] = v if isinstance(v, list) else [str(v)]
            except (TypeError, ValueError):
                pass

        group_key = group.lower()
        if group_key in self._active_exams:
            exam = self._active_exams[group_key]
            # Проверка времени (пункт 16 аудита)
            # ⚠ ВАЖНО: используем exam_start_time (якорь первой попытки),
            # а НЕ connect_time. connect_time сбрасывается при ре-коннекте.
            anchor = student.exam_start_time or student.connect_time
            elapsed = (datetime.now() - anchor).total_seconds()
            max_seconds = exam['duration'] * 60 + 60  # +60 сек буфер
            if elapsed > max_seconds:
                sock.write(pack_message({'status': 'error', 'message': 'time_out'}))
                sock.flush()
                self.log_message.emit(f"Результат отклонён: время вышло для {name} ({group})")
                return
            questions_to_use = student.questions if getattr(student, 'questions', None) else exam['questions']
            partial_multiple = exam.get('partial_multiple', True)
        else:
            sock.write(pack_message({'status': 'error', 'message': 'exam_not_active'}))
            sock.flush()
            return

        score = calculate_score(questions_to_use, int_answers, partial_multiple=partial_multiple)
        student.finished = True
        student.score = score
        student.answers = int_answers

        if (name, group) in self._monitor_data:
            self._monitor_data[(name, group)].finished = True
            self._monitor_data[(name, group)].score = score
            self._monitor_data[(name, group)].answers = int_answers

        test_name = ""
        if group_key in self._active_exams:
            exam = self._active_exams[group_key]
            student_key = name.strip().casefold()
            self._attempt_inc(exam, student_key)
            # Якорь времени переходит к следующей попытке — сбрасываем.
            self._attempt_reset_start_time(exam, student_key)
            test_name = exam.get('test_name', '')

        result_entry = {
            'name': name,
            'group': group,
            'score': score,
            'answers': int_answers,
            'test_name': test_name,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        self._results.append(result_entry)
        self._all_results.append(result_entry)

        # Ограничение размера истории (пункт 15 аудита)
        if len(self._all_results) > 10000:
            self._all_results = self._all_results[-10000:]

        self._save_all_results_to_file()

        response = {
            'status': 'result_confirmed',
            'score': score
        }
        sock.write(pack_message(response))
        sock.flush()

        self.student_finished.emit(name, group, score)
        self.log_message.emit(f"Завершил: {name} ({group}) — {score}")

    @Slot()
    def _on_disconnected(self, sock: QTcpSocket):
        self._pending_buffers.pop(sock, None)
        student = self._students.pop(sock, None)
        if student:
            self.log_message.emit(f"Отключён: {student.name}")
            student.active = False
            # Обновляем в мониторинге
            if (student.name, student.group) in self._monitor_data:
                self._monitor_data[(student.name, student.group)].active = False
            self.student_disconnected.emit(student.name, student.group)
        sock.deleteLater()

    # -- Экспорт результатов --

    def _export_results_csv(self):
        """Сохраняет результаты текущего экзамена в CSV-файл."""
        from PySide6.QtCore import QSettings
        settings = QSettings("EduTest", "Server")
        if not settings.value("auto_export_csv", True, type=bool):
            return

        if not self._results:
            self.log_message.emit("Нет результатов для экспорта.")
            return

        date_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
        group_safe = safe_test_filename(self._allowed_group).removesuffix('.json')
        filename = project_root() / f"Результаты_{group_safe}_{date_str}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'group', 'score', 'timestamp'], extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self._results)
            self.log_message.emit(f"Результаты сохранены: {filename}")
        except Exception as exc:
            self.server_error.emit(f"Ошибка сохранения CSV: {exc}")

    # -- Персистентная история результатов --

    def _load_all_results_from_file(self):
        import json
        path = results_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._all_results = json.load(f)
                self.log_message.emit(f"Загружена история результатов: {len(self._all_results)} записей.")
            except Exception as e:
                self.log_message.emit(f"Ошибка чтения истории результатов: {e}")

    def _save_all_results_to_file(self):
        """Атомарная запись истории результатов.

        Без атомарности крах процесса (или потеря питания) посреди
        json.dump() оставлял бы половину файла на диске → при следующем
        запуске _load_all_results_from_file ловил бы JSONDecodeError и
        теряла
        """
        import json
        path = results_path()
        try:
            tmp_path = path.with_suffix('.tmp')
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self._all_results, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
        except Exception as e:
            self.log_message.emit(f"Ошибка записи истории результатов: {e}")

    def clear_all_results(self):
        self._all_results.clear()
        self._save_all_results_to_file()
        self.log_message.emit("Вся история результатов очищена.")

    def check_for_updates(self) -> tuple[Optional[dict], Optional[str]]:
        """
        Проверяет наличие новых версий на GitHub.
        Возвращает (update_data, error_message).
        """
        import json
        import urllib.request
        import ssl
        import urllib.error
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        req = urllib.request.Request(url, headers={'User-Agent': 'EduTest-Server'})

        # Сначала пробуем верифицированное соединение
        try:
            ssl_context = _verified_ssl_context()
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get("tag_name", "").lstrip("v")

                if not latest_version:
                    return None, "Не удалось определить версию в GitHub релизе"

                if latest_version != VERSION:
                    return data, None
                else:
                    return data, "latest"
        except Exception as e:
            # Проверяем, является ли ошибка связанной с сертификатами
            is_ssl_err = False
            if isinstance(e, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(e):
                is_ssl_err = True
            elif isinstance(e, urllib.error.URLError) and isinstance(e.reason, ssl.SSLError):
                is_ssl_err = True
            elif isinstance(e, urllib.error.URLError) and "CERTIFICATE_VERIFY_FAILED" in str(e.reason):
                is_ssl_err = True

            if is_ssl_err:
                self.log_message.emit("⚠️ Проверка SSL-сертификата GitHub не удалась. Попытка обхода через незащищенное соединение (безопасность гарантируется Ed25519 подписью файлов)...")
                try:
                    unverified_ctx = ssl._create_unverified_context()
                    with urllib.request.urlopen(req, timeout=10, context=unverified_ctx) as response:
                        data = json.loads(response.read().decode())
                        latest_version = data.get("tag_name", "").lstrip("v")

                        if not latest_version:
                            return None, "Не удалось определить версию в GitHub релизе"

                        if latest_version != VERSION:
                            return data, None
                        else:
                            return data, "latest"
                except Exception as fallback_err:
                    e = fallback_err

            err_msg = str(e)
            if "403" in err_msg:
                err_msg = "Превышен лимит запросов GitHub API (403). Это часто происходит из-за общего IP при использовании VPN, Cloudflare WARP или корпоративной сети. Пожалуйста, временно отключите VPN и попробуйте снова."
            elif "110" in err_msg or "timed out" in err_msg.lower():
                err_msg = "Превышено время ожидания ответа от GitHub. Проверьте интернет-соединение."
            self.log_message.emit(f"Ошибка при проверке обновлений: {err_msg}")
            return None, err_msg

    def download_asset(self, url: str, dest_path: str, progress_callback=None):
        """Скачивает файл по ссылке с поддержкой User-Agent и оповещением прогресса."""
        import urllib.request
        import ssl
        import urllib.error
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        req = urllib.request.Request(url, headers={'User-Agent': 'EduTest-Server'})

        # Сначала пробуем верифицированное соединение
        try:
            ssl_context = _verified_ssl_context()
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                with open(dest_path, 'wb') as out_file:
                    while True:
                        chunk = response.read(1024 * 64)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            percent = int((downloaded / total_size) * 100)
                            try:
                                progress_callback(percent, downloaded, total_size)
                            except Exception:
                                pass
            return True
        except Exception as e:
            # Проверяем, является ли ошибка связанной с сертификатами
            is_ssl_err = False
            if isinstance(e, ssl.SSLError) or "CERTIFICATE_VERIFY_FAILED" in str(e):
                is_ssl_err = True
            elif isinstance(e, urllib.error.URLError) and isinstance(e.reason, ssl.SSLError):
                is_ssl_err = True
            elif isinstance(e, urllib.error.URLError) and "CERTIFICATE_VERIFY_FAILED" in str(e.reason):
                is_ssl_err = True

            if is_ssl_err:
                self.log_message.emit("⚠️ Проверка SSL-сертификата GitHub не удалась при скачивании. Попытка обхода через незащищенное соединение...")
                try:
                    unverified_ctx = ssl._create_unverified_context()
                    with urllib.request.urlopen(req, timeout=30, context=unverified_ctx) as response:
                        total_size = int(response.info().get('Content-Length', 0))
                        downloaded = 0
                        with open(dest_path, 'wb') as out_file:
                            while True:
                                chunk = response.read(1024 * 64)
                                if not chunk:
                                    break
                                out_file.write(chunk)
                                downloaded += len(chunk)
                                if progress_callback and total_size > 0:
                                    percent = int((downloaded / total_size) * 100)
                                    try:
                                        progress_callback(percent, downloaded, total_size)
                                    except Exception:
                                        pass
                    return True
                except Exception as fallback_err:
                    e = fallback_err

            self.log_message.emit(f"Ошибка при скачивании {url}: {e}")
            return False

    def _send_chunked_update(self, sock: QTcpSocket, upd_file: str, name: str, client_os: str):
        """Совместимый алиас — вся логика теперь в send_update_to_socket."""
        return self.send_update_to_socket(sock, upd_file, name, client_os)

    def send_update_to_socket(
        self,
        sock: QTcpSocket,
        upd_file: str,
        name: str,
        client_os: str,
        version_tag: str = "",
        client_version: tuple = (1, 3, 5),
        progress_cb=None,
        apply_immediately: bool = True,
    ) -> bool:
        """
        Унифицированная отправка обновления одному клиенту.

        Используется обоими путями — `broadcast_update` (server/main.py)
        и кнопкой «Обновить клиентов» из UI настроек (server/ui_settings.py).

        Выбирает single-packet или chunked в зависимости от размера файла
        и версии клиента. Подписывает payload Ed25519, считает SHA-256.
        Если передан progress_cb(pct: int, text: str) — вызывает его на
        каждом этапе для отображения в UI.
        """
        import base64
        file_size = os.path.getsize(upd_file)
        version_field = version_tag or VERSION

        def _progress(pct: int, text: str):
            if progress_cb:
                try:
                    progress_cb(pct, text)
                except Exception:
                    pass

        _progress(0, "Чтение файла...")
        with open(upd_file, 'rb') as f:
            file_bytes = f.read()

        # Считаем хэш и подпись всего бинарника. Клиент сверит хэш после
        # последнего чанка и подпись до запуска обновления — это закрывает
        # подмену сервера в LAN (см. SECURITY.md).
        file_hash = sha256_hex(file_bytes)
        signature_b64 = self._sign_update_bytes(upd_file, file_bytes)

        estimated_b64_size = int(file_size * 1.37) + 1024
        use_single_packet = (
            estimated_b64_size <= OLD_CLIENT_MAX_SIZE
            and (client_version < (1, 3, 5) or estimated_b64_size <= UPDATE_CHUNK_SIZE)
        )

        # --- Ветка 1: одним пакетом (маленькие файлы / совместимость со старым клиентом) ---
        if use_single_packet:
            _progress(20, "Кодирование (base64)...")
            payload_b64 = base64.b64encode(file_bytes).decode()
            from shared.security import get_public_key_pem
            packet = {
                'status': 'update_available' if apply_immediately else 'update_download',
                'version': version_field,
                'filename': os.path.basename(upd_file),
                'payload': payload_b64,
                'sha256': file_hash,
                'signature': signature_b64,
                'sig_algo': 'ed25519' if signature_b64 else None,
                'public_key': get_public_key_pem(),
            }
            _progress(60, "Отправка пакета...")
            sock.write(pack_message(packet))
            sock.flush()
            _progress(100, "Передача завершена!")
            self.log_message.emit(
                f"Отправлено обновление одним пакетом клиенту {name} ({client_os}): "
                f"{file_size // 1024} КБ, подпись={'есть' if signature_b64 else 'НЕТ'}"
            )
            return True

        # --- Ветка 2: чанковая отправка (большой файл + современный клиент) ---
        if client_version < (1, 3, 5):
            _progress(100, f"⚠️ Пропущено: v{'.'.join(map(str, client_version))} не поддерживает chunked")
            self.log_message.emit(
                f"⚠️ Пропущено обновление для {name}: версия {client_version} "
                f"не поддерживает чанковую загрузку, файл слишком велик для legacy-пакета."
            )
            return False

        total_chunks = (file_size + UPDATE_CHUNK_SIZE - 1) // UPDATE_CHUNK_SIZE

        from shared.security import get_public_key_pem
        start_packet = {
            'status': 'update_start',
            'version': version_field,
            'filename': os.path.basename(upd_file),
            'total_chunks': total_chunks,
            'file_size': file_size,
            'sha256': file_hash,
            'signature': signature_b64,
            'sig_algo': 'ed25519' if signature_b64 else None,
            'public_key': get_public_key_pem(),
        }
        sock.write(pack_message(start_packet))
        sock.flush()

        offset = 0
        mb_total = file_size / (1024 * 1024)
        for i in range(total_chunks):
            chunk = file_bytes[offset:offset + UPDATE_CHUNK_SIZE]
            offset += UPDATE_CHUNK_SIZE
            sock.write(pack_message({
                'status': 'update_chunk',
                'chunk_index': i,
                'payload': base64.b64encode(chunk).decode(),
            }))
            sock.flush()
            pct = int(((i + 1) / total_chunks) * 100)
            mb_sent = min((i + 1) * UPDATE_CHUNK_SIZE, file_size) / (1024 * 1024)
            _progress(pct, f"Передача: {pct}% ({mb_sent:.1f} / {mb_total:.1f} МБ)")

        from shared.security import get_public_key_pem
        sock.write(pack_message({
            'status': 'update_complete',
            'sha256': file_hash,
            'signature': signature_b64,
            'sig_algo': 'ed25519' if signature_b64 else None,
            'apply': apply_immediately,
            'public_key': get_public_key_pem(),
        }))
        sock.flush()
        _progress(100, "Передача завершена!")

        self.log_message.emit(
            f"Отправлено чанковое обновление клиенту {name} ({client_os}): "
            f"{total_chunks} чанков, {file_size // 1024 // 1024} МБ, "
            f"подпись={'есть' if signature_b64 else 'НЕТ — клиент откажется ставить'}"
        )
        return True

    # -----------------------------------------------------------------
    # Поиск приватного ключа подписи обновлений.
    # -----------------------------------------------------------------
    def _sign_update_bytes(self, upd_file: str, payload: bytes) -> Optional[str]:
        """
        Возвращает base64-подпись Ed25519 для бинарника обновления.

        Источники подписи (в порядке приоритета):
          1) Сосед `<upd_file>.sig` — например, создан `scripts/sign_update.py`
             в CI и положен рядом с .exe/.bin. Это рекомендуемый путь.
          2) Приватный ключ из env `EDUTEST_PRIVATE_KEY`.
          3) `~/.edutest/update_private_key.pem`.

        Если ничего не нашли — возвращаем None и пишем предупреждение в лог.
        Клиент в таком случае откажется применять обновление.
        """
        sig_path = upd_file + ".sig"
        if os.path.isfile(sig_path):
            try:
                return open(sig_path, 'r', encoding='utf-8').read().strip() or None
            except OSError as exc:
                self.log_message.emit(f"Не удалось прочитать {sig_path}: {exc}")

        key_candidates = []
        env_key = os.environ.get("EDUTEST_PRIVATE_KEY")
        if env_key:
            key_candidates.append(env_key)
        key_candidates.append(os.path.expanduser("~/.edutest/update_private_key.pem"))

        # Проверим наличие хоть одного приватного ключа. Если нет - генерируем.
        has_key = False
        for kp in key_candidates:
            if os.path.isfile(kp):
                has_key = True
                break

        if not has_key:
            self.log_message.emit("⚠️ Приватный ключ подписи не найден. Автоматическая генерация новой пары ключей...")
            try:
                from shared.security import generate_and_save_keys
                priv_path, pub_path = generate_and_save_keys()
                self.log_message.emit(f"✅ Успешно сгенерирована новая пара ключей.")
                self.log_message.emit(f"   Приватный: {priv_path}")
                self.log_message.emit(f"   Публичный: {pub_path}")
            except Exception as e:
                self.log_message.emit(f"❌ Не удалось автоматически сгенерировать ключи подписи: {e}")

        for kp in key_candidates:
            if os.path.isfile(kp):
                try:
                    pk = load_private_key(kp)
                    return sign_bytes(pk, payload)
                except Exception as exc:
                    self.log_message.emit(
                        f"Не удалось подписать обновление ключом {kp}: {exc}"
                    )

        self.log_message.emit(
            "⚠️ Приватный ключ подписи не найден. Обновление НЕ будет подписано — "
            "клиенты с публичным ключом его отклонят. Подробнее: SECURITY.md."
        )
        return None

    def get_updates_dir(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "updates")

    def broadcast_update(self):
        """Рассылает пакет обновления всем подключенным студентам."""
        upd_dir = self.get_updates_dir()
        if not os.path.exists(upd_dir):
            return

        # Находим файлы обновлений для каждой ОС
        update_files = {}  # os_name -> file_path
        for f in os.listdir(upd_dir):
            path = os.path.join(upd_dir, f)
            if f.lower().endswith('.exe'):
                update_files['windows'] = path
            elif 'student' in f.lower():
                update_files['linux'] = path

        if not update_files:
            return

        count = 0
        for sock, student in self._students.items():
            client_os = getattr(student, 'os', 'windows')
            upd_file = update_files.get(client_os)
            if not upd_file:
                continue

            client_ver = _version_tuple(getattr(student, 'version', '0.0.0'))
            sent = self.send_update_to_socket(
                sock=sock,
                upd_file=upd_file,
                name=student.name,
                client_os=client_os,
                version_tag=VERSION,
                client_version=client_ver,
            )
            if sent:
                count += 1

        self.log_message.emit(f"Массовое обновление запущено для {count} клиентов.")

    def prepare_update_payloads(self) -> dict:
        """Подготавливает закодированные в base64 пакеты обновления для ОС."""
        upd_dir = self.get_updates_dir()
        updates = {}
        if not os.path.exists(upd_dir):
            return updates

        import base64
        for f in os.listdir(upd_dir):
            path = os.path.join(upd_dir, f)
            if f.lower().endswith('.exe'):
                try:
                    with open(path, 'rb') as rb:
                        updates['windows'] = base64.b64encode(rb.read()).decode()
                        updates['windows_name'] = f
                except Exception:
                    pass
            elif 'student' in f.lower():
                try:
                    with open(path, 'rb') as rb:
                        updates['linux'] = base64.b64encode(rb.read()).decode()
                        updates['linux_name'] = f
                except Exception:
                    pass
        return updates

    def send_reboot_to_all_clients(self):
        """Отправляет сигнал принудительной перезагрузки на обновление всем клиентам."""
        from shared.protocol import pack_message
        packet = {'status': 'update_apply'}
        for sock in list(self._students.keys()):
            try:
                sock.write(pack_message(packet))
                sock.flush()
            except Exception:
                pass


def get_resource_path(relative_path):
    """Получает абсолютный путь к ресурсу, работает для обычного запуска и для Nuitka/PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Для Nuitka
    base_path = os.path.dirname(os.path.abspath(__file__))
    # Если мы в папке server/, ищем в корне проекта
    potential_path = os.path.join(base_path, "..", relative_path)
    if os.path.exists(potential_path):
        return os.path.abspath(potential_path)
    return os.path.abspath(os.path.join(base_path, relative_path))


def main():
    """Запуск приложения сервера преподавателя."""
    app = QApplication(sys.argv)
    app.setApplicationName("TTGTiSO-Test — Сервер")
    app.setOrganizationName("EduTest")

    # Установка иконки приложения
    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QIcon, QPixmap
    icon_set = False
    try:
        from shared.icon_data import ICON_BASE64
        ba = QByteArray.fromBase64(ICON_BASE64.encode('utf-8'))
        pixmap = QPixmap()
        if pixmap.loadFromData(ba):
            app.setWindowIcon(QIcon(pixmap))
            icon_set = True
    except Exception as e:
        print(f"Ошибка загрузки встроенной иконки: {e}")

    if not icon_set:
        icon_candidates = [
            get_resource_path("image.ico"),
            get_resource_path("image.png"),
            os.path.join(os.path.dirname(sys.executable), "image.ico"),
            "/opt/test_system_server/icon.png"
        ]
        for path in icon_candidates:
            if os.path.exists(path):
                app.setWindowIcon(QIcon(path))
                break

    # Создаём сервер экзаменов
    exam_server = ExamServer()
    exam_server.start_background_listening()

    # Импортируем и создаём GUI
    from ui_server import ServerWindow
    window = ServerWindow(exam_server)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
