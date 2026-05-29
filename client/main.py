"""
client/main.py — Точка входа клиента студента.
Сетевая логика (TCP), подключение к серверу, отправка результатов,
шифрованный локальный бэкап.
"""

import json
import os
import platform
import struct
import sys
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QByteArray, QObject, Signal, Slot
from PySide6.QtNetwork import QAbstractSocket, QNetworkProxy, QTcpSocket
from PySide6.QtWidgets import QApplication

MAX_MESSAGE_SIZE = 64 * 1024 * 1024  # 64 МБ. До 1.3.7 было 500 МБ —
                                     # достаточно для DoS на клиент.

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.protocol import pack_message
from shared.security import has_public_key, sha256_hex, verify_signature
from shared.version import VERSION


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


def save_encrypted_backup(name: str, group: str, score: str, answers: dict, test_name: str = ""):
    """Сохраняет результат в зашифрованном .log файле."""
    data = {
        'name': name,
        'group': group,
        'score': score,
        'answers': answers,
        'test_name': test_name,
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


def save_student_final_backup(name: str, group: str, score: str, answers: dict, test_name: str = "") -> Optional[str]:
    """
    Создает видимую папку 'резервная копия' в текущей директории запуска
    и экспортирует туда зашифрованный лог с ФИО студента и группой в названии.
    """
    try:
        def sanitize(val: str) -> str:
            return "".join(c for c in val if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')

        safe_name = sanitize(name)
        safe_group = sanitize(group)
        if not safe_name:
            safe_name = "Студент"
        if not safe_group:
            safe_group = "Группа"

        # Папка 'резервная копия' в текущей папке запуска
        backup_dir = os.path.join(os.getcwd(), "резервная копия")
        os.makedirs(backup_dir, exist_ok=True)

        data = {
            'name': name,
            'group': group,
            'score': score,
            'answers': answers,
            'test_name': test_name,
            'timestamp': datetime.now().isoformat(),
        }
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
        encrypted = xor_encrypt(raw)

        filename = f"Бэкап_{safe_group}_{safe_name}.log"
        filepath = os.path.join(backup_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(encrypted)

        return filepath
    except Exception as e:
        print(f"Ошибка при сохранении резервной копии: {e}")
        return None


class StudentClient(QObject):
    """
    TCP-клиент студента.

    Signals:
        connected_ok(list, int)     — вопросы (payload) и длительность (мин)
        connection_error(str)       — ошибка подключения
        result_sent()               — результат успешно отправлен
        log_message(str)
    """

    connected_ok = Signal(list, int, str, str, str, int, int)  # questions, duration, title, section, test_name, remaining_seconds, cheat_warning_limit
    connection_error = Signal(str)           # message
    result_sent = Signal(str)                # score calculated by server
    force_stopped = Signal()                 # force stopped by teacher
    log_message = Signal(str)
    active_group_found = Signal(list)        # active groups
    update_received = Signal(str)            # version
    attempts_checked_signal = Signal(int, int) # attempts_left, max_attempts
    update_progress_signal = Signal(int, str) # percent, text_status

    def __init__(self, parent=None):
        super().__init__(parent)
        self._socket = QTcpSocket(self)
        self._socket.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
        self._socket.connected.connect(self._on_socket_connected)
        self._socket.disconnected.connect(self._on_socket_disconnected)
        self._socket.readyRead.connect(self._on_data_ready)
        self._socket.errorOccurred.connect(self._on_socket_error)

        self._buffer = QByteArray()
        self._name = ''
        self._group = ''
        self._test_name = ''
        self._pending_connect = False
        self._intentional_disconnect = False
        self._temp_sock = None
        self._temp_buf = QByteArray()
        # Состояние чанковой загрузки обновлений
        self._update_file_path = ''
        self._update_total_chunks = 0
        self._update_received_chunks = 0
        self._update_expected_sha256: Optional[str] = None
        self._update_signature: Optional[str] = None
        self._update_sig_algo: Optional[str] = None

    def check_active_group(self, host: str, port: int):
        """Запрашивает с сервера активные группы без входа."""
        if self._temp_sock is not None:
            try:
                self._temp_sock.disconnectFromHost()
                self._temp_sock.deleteLater()
            except Exception:
                pass
        self._temp_sock = QTcpSocket(self)
        self._temp_sock.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
        self._temp_buf = QByteArray()

        def on_connected():
            packet = {'action': 'get_active_group'}
            self._temp_sock.write(pack_message(packet))
            self._temp_sock.flush()

        def on_ready_read():
            self._temp_buf.append(self._temp_sock.readAll())
            while len(self._temp_buf) >= 4:
                msg_len = struct.unpack('!I', self._temp_buf[:4].data())[0]
                if msg_len > MAX_MESSAGE_SIZE:
                    self.active_group_found.emit([])
                    self._temp_sock.disconnectFromHost()
                    return
                if len(self._temp_buf) < 4 + msg_len:
                    break
                raw = self._temp_buf[4:4 + msg_len].data()
                self._temp_buf = self._temp_buf[4 + msg_len:]
                try:
                    res = json.loads(raw.decode('utf-8'))
                    if res.get('status') == 'success':
                        groups = res.get('groups')
                        if not isinstance(groups, list):
                            group = res.get('group', '')
                            groups = [g.strip() for g in group.split(",") if g.strip()]
                        self.active_group_found.emit([str(g).strip() for g in groups if str(g).strip()])
                    elif res.get('message') == 'exam_not_active':
                        self.active_group_found.emit([])
                except (UnicodeDecodeError, json.JSONDecodeError):
                    self.active_group_found.emit([])
                self._temp_sock.disconnectFromHost()

        self._temp_sock.connected.connect(on_connected)
        self._temp_sock.readyRead.connect(on_ready_read)
        self._temp_sock.errorOccurred.connect(lambda error: self.active_group_found.emit([]))
        self._temp_sock.connectToHost(host.strip(), port)

    def connect_to_server(self, host: str, port: int, name: str, group: str):
        self._name = name.strip()
        self._group = group.strip()
        self._pending_connect = True
        self._intentional_disconnect = False
        self._buffer.clear()
        self._socket.abort()  # Сброс предыдущего состояния подключения
        self._socket.connectToHost(host.strip(), port)

    def connect_to_server_idle(self, host: str, port: int):
        self._name = ""
        self._group = ""
        self._pending_connect = True
        self._intentional_disconnect = False
        self._buffer.clear()
        self._socket.abort()
        print(f"[DEBUG] Инициализация фонового дежурного подключения к {host}:{port}...")
        self._socket.connectToHost(host.strip(), port)

    @Slot()
    def _on_socket_connected(self):
        if self._pending_connect:
            self._pending_connect = False
            packet = {
                'action': 'connect',
                'name': self._name,
                'group': self._group,
                'version': VERSION,
                'os': platform.system().lower()
            }
            print(f"[DEBUG] Сокет подключен к серверу. Отправка пакета: {packet}")
            self._socket.write(pack_message(packet))
            self._socket.flush()

    @Slot()
    def _on_data_ready(self):
        self._buffer.append(self._socket.readAll())

        while len(self._buffer) >= 4:
            msg_len = struct.unpack('!I', self._buffer[:4].data())[0]
            if msg_len > MAX_MESSAGE_SIZE:
                self.connection_error.emit('Сервер отправил слишком большой пакет')
                self._socket.disconnectFromHost()
                return
            if len(self._buffer) < 4 + msg_len:
                break
            raw = self._buffer[4:4 + msg_len].data()
            self._buffer = self._buffer[4 + msg_len:]
            try:
                packet = json.loads(raw.decode('utf-8'))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            self._handle_response(packet)

    def _handle_response(self, packet: dict):
        status = packet.get('status')
        if status == 'success':
            questions = packet.get('questions', [])
            duration = packet.get('duration', 60)
            title = packet.get('title', 'Итоговое тестирование')
            section = packet.get('section', 'Раздел: Основная часть')
            test_name = packet.get('test_name', '')
            self._test_name = test_name
            # remaining_seconds приходит от сервера, если он умеет (v1.3.7+).
            # Для совместимости со старым сервером — fallback на duration*60.
            remaining = packet.get('remaining_seconds')
            if remaining is None:
                remaining = duration * 60
            cheat_warning_limit = packet.get('cheat_warning_limit', 3)
            self.connected_ok.emit(questions, duration, title, section, test_name, int(remaining), int(cheat_warning_limit))
        elif status == 'result_confirmed':
            score = packet.get('score', '0/0')
            self.result_sent.emit(score)
        elif status == 'force_stopped':
            self.force_stopped.emit()
        elif status == 'update_available':
            self._apply_update(packet)
        elif status == 'update_download':
            self._save_update_file(packet)
        elif status == 'update_apply':
            # Преподаватель нажал «Применить обновление сейчас».
            # Перепроверяем .new по sidecar-метаданным — даже если файл
            # уже был проверен при загрузке, между этим и сейчас он мог
            # быть повреждён (упал процесс, обрыв сети, ручное вмеша
            expected_new = os.path.abspath(sys.argv[0]) + ".new"
            if not os.path.exists(expected_new):
                self.log_message.emit(
                    "⚠️ Получен файл обновления, но он не существует. "
                    "Обновление отклонено."
                )
                return
            if not self._verify_update_bytes(
                open(expected_new, 'rb').read(),
                expected_sha256=packet.get('sha256'),
                signature_b64=packet.get('signature'),
                sig_algo=packet.get('sig_algo'),
            ):
                try:
                    os.remove(expected_new)
                except OSError:
                    pass
                self.log_message.emit(
                    "⚠️ Получен файл обновления, но он не валиден. "
                    "Обновление отклонено."
                )
                return
            self._run_updater()
        elif status == 'update_start':
            self._handle_update_start(packet)
        elif status == 'update_chunk':
            self._handle_update_chunk(packet)
        elif status == 'update_complete':
            self._handle_update_complete(packet)
        elif status == 'idle_connected':
            pass
        elif status == 'error':
            msg = packet.get('message', 'unknown')
            if msg == 'wrong_group':
                self.connection_error.emit(
                    'Вы не числитесь в текущей группе тестирования'
                )
            elif msg == 'exam_not_active':
                self.connection_error.emit('Тестирование ещё не запущено')
            elif msg == 'empty_fields':
                self.connection_error.emit('Заполните все поля')
            elif msg == 'attempts_exceeded':
                self.connection_error.emit('Лимит попыток для этого теста исчерпан')
            elif msg == 'duplicate_connection':
                self.connection_error.emit('Этот студент уже проходит тест')
            elif msg == 'not_connected':
                self.connection_error.emit('Результат отклонён: клиент не подключён к тестированию')
            elif msg == 'invalid_answers':
                self.connection_error.emit('Результат отклонён: неверный формат ответов')
            elif msg == 'time_out':
                self.connection_error.emit('Время на выполнение теста истекло')
            else:
                self.connection_error.emit(f'Ошибка сервера: {msg}')

    @Slot()
    def _on_socket_disconnected(self):
        if not self._intentional_disconnect:
            if not self._name and not self._group:
                return
            self.connection_error.emit('Соединение с сервером потеряно')

    @Slot(QAbstractSocket.SocketError)
    def _on_socket_error(self, error):
        if not self._name and not self._group:
            return
        err_str = self._socket.errorString()
        self.connection_error.emit(
            f'Не удалось подключиться к серверу ({err_str}).\n\n'
            f'Рекомендации по устранению:\n'
            f'1. Убедитесь, что IP-адрес сервера и порт введены правильно.\n'
            f'2. Убедитесь, что преподаватель запустил тестирование на сервере.\n'
            f'3. Проверьте, что компьютер студента и компьютер преподавателя находятся в одной сети.\n'
            f'4. Убедитесь, что брандмауэр на компьютере преподавателя не блокирует порт {self._socket.peerPort() if self._socket.peerPort() > 0 else 9876}.'
        )

    def send_result(self, answers: dict) -> bool:
        """Отправляет ответы на сервер для точного расчёта."""
        packet = {
            'action': 'result',
            'name': self._name,
            'group': self._group,
            'answers': answers,
        }
        sent = False
        if self._socket.state() == QAbstractSocket.ConnectedState:
            bytes_written = self._socket.write(pack_message(packet))
            self._socket.flush()
            sent = bytes_written != -1

        score_placeholder = f"{len(answers)}"
        save_encrypted_backup(self._name, self._group, score_placeholder, answers, self._test_name)
        return sent

    def send_cheat_warning(self, description: str) -> bool:
        """Отправляет на сервер информацию о нарушении режима киоска (попытка списать)."""
        packet = {
            'action': 'cheat_warning',
            'name': self._name,
            'group': self._group,
            'description': description,
        }
        sent = False
        if self._socket.state() == QAbstractSocket.ConnectedState:
            bytes_written = self._socket.write(pack_message(packet))
            self._socket.flush()
            sent = bytes_written != -1
        return sent

    def save_backup(self, answers: dict, score: str = "N/A"):
        """Позволяет принудительно сохранить локальную резервную копию ответов."""
        save_encrypted_backup(self._name, self._group, score, answers, self._test_name)

    def disconnect(self):
        self._intentional_disconnect = True
        if self._socket.state() == QAbstractSocket.ConnectedState:
            self._socket.disconnectFromHost()

    def _save_update_file(self, packet: dict) -> bool:
        """Декодирует и сохраняет файл обновления в .new.

        Перед записью проверяет:
          * SHA-256 — защита от случайной порчи данных,
          * Ed25519 подпись — защита от MITM-подмены сервера в LAN.

        Если проверки не пройдены — файл .new не создаётся, обновление
        отвергается, в лог пишется причина. Поведение можно отключить
        отдельным флагом в будущем, но по умолчанию — fail closed.
        """
        import base64
        import shutil
        payload = packet.get('payload')
        if not payload:
            return False
        try:
            data = base64.b64decode(payload)
        except Exception as e:
            self.log_message.emit(f"Ошибка декодирования обновления: {e}")
            return False

        if not self._verify_update_bytes(
            data,
            expected_sha256=packet.get('sha256'),
            signature_b64=packet.get('signature'),
            sig_algo=packet.get('sig_algo'),
        ):
            return False

        try:
            current_exe = os.path.abspath(sys.argv[0])
            update_file = current_exe + ".new"
            target_dir = os.path.dirname(update_file) or "."

            # Защита G: проверка прав на запись.
            if not os.access(target_dir, os.W_OK):
                self.log_message.emit(
                    f"❌ Нет прав на запись в {target_dir}"
                )
                return False

            # Защита G: проверка свободного места (нужно >= 1.5×file_size).
            file_size = len(data)
            disk_usage = shutil.disk_usage(target_dir)
            if disk_usage.free < file_size * 1.5:
                self.log_message.emit(
                    f"❌ Недостаточно места на диске: нужно >= {file_size * 1.5} байт, "
                    f"свободно {disk_usage.free} байт"
                )
                return False

            with open(update_file, 'wb') as f:
                f.write(data)

            # Sidecar-метаданные: .sha256 и .sig рядом с .new.
            # Нужны для повторной проверки в update_apply — если процесс
            # упал между загрузкой и применением, мы не запустим .new
            # без подтверждённой подписи.
            expected_sha256 = packet.get('sha256')
            if expected_sha256:
                with open(update_file + '.sha256', 'w') as f:
                    f.write(expected_sha256)
            signature_b64 = packet.get('signature')
            if signature_b64:
                with open(update_file + '.sig', 'w') as f:
                    f.write(signature_b64)
            return True
        except Exception as e:
            self.log_message.emit(f"Ошибка при сохранении обновления: {e}")
            return False

    def _verify_update_bytes(
        self,
        data: bytes,
        expected_sha256: Optional[str],
        signature_b64: Optional[str],
        sig_algo: Optional[str],
    ) -> bool:
        """
        Проверяет, что бинарник обновления подлинный и не повреждён.

        Если в клиента не встроен публичный ключ (shared/update_public_key.pem),
        мы временно разрешаем установку, но громко логируем предупреждение.
        Это даёт обратную совместимость с серверами, которые не успели
        развернуть подпись. Когда вы выкатите подписанные сборки, обновите
        проверку на fail-closed (см. SECURITY.md).
        """
        if expected_sha256:
            actual = sha256_hex(data)
            if actual.lower() != str(expected_sha256).lower():
                self.log_message.emit(
                    f"❌ Хэш обновления не совпадает: ожидался {expected_sha256}, "
                    f"получен {actual}. Обновление отклонено."
                )
                return False

        if has_public_key():
            if sig_algo and sig_algo.lower() != 'ed25519':
                self.log_message.emit(
                    f"❌ Неизвестный алгоритм подписи: {sig_algo!r}. Обновление отклонено."
                )
                return False
            if not signature_b64:
                self.log_message.emit(
                    "❌ Сервер прислал обновление без подписи, но клиент "
                    "сконфигурирован проверять подпись. Обновление отклонено."
                )
                return False
            if not verify_signature(data, signature_b64):
                self.log_message.emit(
                    "❌ Подпись Ed25519 не валидна. Возможна подмена сервера. "
                    "Обновление отклонено."
                )
                return False
            self.log_message.emit("✅ Подпись обновления подтверждена.")
        elif signature_b64:
            self.log_message.emit(
                "⚠️ Сервер прислал подпись, но в клиенте нет публичного ключа — "
                "проверить не можем. Доверяем, но обновитесь до сборки с ключом."
            )
        else:
            self.log_message.emit(
                "⚠️ Обновление пришло БЕЗ ПОДПИСИ. Это небезопасно (см. SECURITY.md). "
                "Доверяем только потому, что у клиента нет встроенного ключа."
            )
        return True

    def _run_updater(self):
        """Запускает скрипт замены и перезагружает приложение.

        Скрипт создаётся в системной temp-директории (а не в CWD —
        иначе при запуске exe из меню Пуск с CWD=C:\\Windows\\System32
        мы бы пытались писать в системную папку). Пути экранируются
        кавычками, чтобы корректно работать с 'Program Files' и
        прочими директориями с пробелами.
        """
        import subprocess
        try:
            current_exe = os.path.abspath(sys.argv[0])
            update_file = current_exe + ".new"

            # Если запущен скрипт .py, мы не заменяем его бинарным файлом.
            # Просто перезапускаем текущий .py с помощью sys.executable.
            if current_exe.endswith('.py'):
                try:
                    if os.path.exists(update_file):
                        os.remove(update_file)
                except Exception:
                    pass
                if platform.system() == 'Windows':
                    subprocess.Popen([sys.executable, current_exe])
                else:
                    subprocess.Popen([sys.executable, current_exe])
                QApplication.quit()
                return

            if not os.path.exists(update_file):
                self.log_message.emit("Ошибка: файл обновления .new не найден.")
                return

            import tempfile
            tmp_dir = tempfile.gettempdir()

            if platform.system() == 'Windows':
                # Скрипт пишется в %TEMP%, а не в CWD — иначе exe, запущенный
                # из меню Пуск (CWD = C:\Windows\System32), пытался бы писать
                # в системную папку. Все пути экранируются кавычками, чтобы
                # корректно обрабатывать "Program Files" и т.п.
                fd, updater_script = tempfile.mkstemp(suffix='.bat', prefix='edutest_update_', dir=tmp_dir)
                os.close(fd)
                with open(updater_script, 'w', encoding='utf-8') as f:
                    f.write('@echo off\n')
                    f.write('timeout /t 2 /nobreak > nul\n')
                    f.write(f'del "{current_exe}"\n')
                    f.write(f'move "{update_file}" "{current_exe}"\n')
                    f.write(f'start "" "{current_exe}"\n')
                    f.write('del "%~f0"\n')
                # cmd /c вместо shell=True — безопаснее работает с пробелами в путях.
                subprocess.Popen(
                    ['cmd.exe', '/c', updater_script],
                    shell=False,
                    creationflags=getattr(subprocess, 'DETACHED_PROCESS', 0),
                )
            else:
                fd, updater_script = tempfile.mkstemp(suffix='.sh', prefix='edutest_update_', dir=tmp_dir)
                os.close(fd)
                with open(updater_script, 'w', encoding='utf-8') as f:
                    f.write('#!/bin/bash\n')
                    f.write('sleep 2\n')
                    f.write(f'mv "{update_file}" "{current_exe}"\n')
                    f.write(f'chmod +x "{current_exe}"\n')
                    f.write(f'"{current_exe}" &\n')
                    f.write('rm "$0"\n')
                os.chmod(updater_script, 0o755)
                subprocess.Popen(['/bin/bash', updater_script])

            self.update_received.emit(VERSION)
            QApplication.quit()
        except Exception as e:
            self.log_message.emit(f"Ошибка при перезапуске обновления: {e}")

    def _apply_update(self, packet: dict):
        """Сохраняет обновление и сразу запускает скрипт замены (обратная совместимость)."""
        if self._save_update_file(packet):
            self._run_updater()

    def _handle_update_start(self, packet: dict):
        """Начало чанковой загрузки обновления — создаём пустой файл .new."""
        self._update_total_chunks = packet.get('total_chunks', 0)
        self._update_received_chunks = 0
        self._update_file_path = os.path.abspath(sys.argv[0]) + ".new"
        target_dir = os.path.dirname(self._update_file_path) or "."

        # Проверки прав и места — тот же набор, что и в _save_update_file.
        file_size = packet.get('file_size', 0)
        if not os.access(target_dir, os.W_OK):
            self.log_message.emit(
                f"❌ Нет прав на запись в {target_dir}"
            )
            return
        import shutil
        disk_usage = shutil.disk_usage(target_dir)
        if disk_usage.free < file_size * 1.5:
            self.log_message.emit(
                f"❌ Недостаточно места на диске: нужно >= {file_size * 1.5} байт, "
                f"свободно {disk_usage.free} байт"
            )
            return
        # Метаданные подписи — будут проверены в _handle_update_complete.
        self._update_expected_sha256 = packet.get('sha256')
        self._update_signature = packet.get('signature')
        self._update_sig_algo = packet.get('sig_algo')
        try:
            with open(self._update_file_path, 'wb') as f:
                pass  # Создаём/очищаем файл
            version = packet.get('version', '?')
            self.log_message.emit(
                f"Начало загрузки обновления v{version}: "
                f"{self._update_total_chunks} чанков, {file_size // 1024 // 1024} МБ"
            )
            self.update_progress_signal.emit(0, f"Подготовка к загрузке обновления (v{version})...")
        except Exception as e:
            self.log_message.emit(f"Ошибка при создании файла обновления: {e}")
            self.update_progress_signal.emit(0, f"Ошибка: {e}")

    def _handle_update_chunk(self, packet: dict):
        """Получен очередной чанк обновления — дописываем в файл .new."""
        import base64
        chunk_data = packet.get('payload', '')
        if not chunk_data:
            return
        try:
            data = base64.b64decode(chunk_data)
            with open(self._update_file_path, 'ab') as f:
                f.write(data)
            self._update_received_chunks += 1

            if self._update_total_chunks > 0:
                percent = int((self._update_received_chunks / self._update_total_chunks) * 100)
                self.update_progress_signal.emit(
                    percent,
                    f"Загрузка обновления: {percent}% ({self._update_received_chunks} из {self._update_total_chunks} частей)"
                )
        except Exception as e:
            self.log_message.emit(f"Ошибка при записи чанка обновления: {e}")
            self.update_progress_signal.emit(0, f"Ошибка записи: {e}")

    def _handle_update_complete(self, packet: Optional[dict] = None):
        """Все чанки получены — проверяем подпись и запускаем процедуру обновления."""
        self.log_message.emit(
            f"Загрузка обновления завершена: "
            f"{self._update_received_chunks}/{self._update_total_chunks} чанков"
        )
        if not (
            self._update_received_chunks == self._update_total_chunks
            and self._update_total_chunks > 0
        ):
            self.log_message.emit("Ошибка: не все чанки обновления получены, обновление отменено.")
            self.update_progress_signal.emit(0, "Ошибка: получены не все данные.")
            return

        # complete-пакет может дублировать sha256/signature — это бекап
        # на случай потерянного start-пакета.
        if packet:
            self._update_expected_sha256 = self._update_expected_sha256 or packet.get('sha256')
            self._update_signature = self._update_signature or packet.get('signature')
            self._update_sig_algo = self._update_sig_algo or packet.get('sig_algo')

        try:
            with open(self._update_file_path, 'rb') as f:
                full_bytes = f.read()
        except OSError as exc:
            self.log_message.emit(f"Не удалось прочитать собранный файл обновления: {exc}")
            self.update_progress_signal.emit(0, "Ошибка чтения файла.")
            return

        if not self._verify_update_bytes(
            full_bytes,
            expected_sha256=self._update_expected_sha256,
            signature_b64=self._update_signature,
            sig_algo=self._update_sig_algo,
        ):
            # Уничтожаем непроверенный .new, чтобы _run_updater не подобрал его потом.
            try:
                os.remove(self._update_file_path)
            except OSError:
                pass
            self.update_progress_signal.emit(0, "Обновление отклонено: проверка не пройдена.")
            return

        self.update_progress_signal.emit(100, "Загрузка завершена! Перезапуск...")

        # Sidecar-метаданные: позволят update_apply повторно проверить файл.
        try:
            if self._update_expected_sha256:
                with open(self._update_file_path + ".sha256", "w") as f:
                    f.write(self._update_expected_sha256)
            if self._update_signature:
                with open(self._update_file_path + ".sig", "w") as f:
                    f.write(self._update_signature)
        except OSError as exc:
            self.log_message.emit(f"⚠️ Не удалось записать sidecar-файлы: {exc}")

        # apply=False означает «просто скачайте, перезагрузит позже»: преподаватель
        # делает это руками из «Скачать обновления». В этом случае мы НЕ запускаем
        # _run_updater сразу — это нормальный путь, .new ждёт команды update_apply.
        should_apply = (packet or {}).get('apply', True)
        if not should_apply:
            self.log_message.emit(
                "✅ Обновление загружено, ждём команды от преподавателя для применения."
            )
            return

        self._run_updater()

    @property
    def student_name(self) -> str:
        return self._name

    @property
    def student_group(self) -> str:
        return self._group

    def get_socket_state(self) -> QAbstractSocket.SocketState:
        return self._socket.state()

    def check_attempts_left(self, host: str, port: int, name: str, group: str):
        """Запрашивает с сервера количество оставшихся попыток студента."""
        import struct

        from shared.protocol import pack_message

        if hasattr(self, '_attempts_sock') and self._attempts_sock is not None:
            try:
                self._attempts_sock.disconnectFromHost()
                self._attempts_sock.deleteLater()
            except Exception:
                pass

        self._attempts_sock = QTcpSocket(self)
        self._attempts_sock.setProxy(QNetworkProxy(QNetworkProxy.NoProxy))
        self._attempts_buf = QByteArray()

        def on_connected():
            packet = {
                'action': 'get_attempts_left',
                'name': name.strip(),
                'group': group.strip()
            }
            self._attempts_sock.write(pack_message(packet))
            self._attempts_sock.flush()

        def on_ready_read():
            self._attempts_buf.append(self._attempts_sock.readAll())
            while len(self._attempts_buf) >= 4:
                msg_len = struct.unpack('!I', self._attempts_buf[:4].data())[0]
                if msg_len > MAX_MESSAGE_SIZE:
                    self._attempts_sock.disconnectFromHost()
                    return
                if len(self._attempts_buf) < 4 + msg_len:
                    break
                raw = self._attempts_buf[4:4 + msg_len].data()
                self._attempts_buf = self._attempts_buf[4 + msg_len:]
                try:
                    res = json.loads(raw.decode('utf-8'))
                    if res.get('status') == 'attempts_left':
                        left = res.get('attempts_left', 0)
                        max_att = res.get('max_attempts', 0)
                        self.attempts_checked_signal.emit(left, max_att)
                except Exception:
                    pass
                self._attempts_sock.disconnectFromHost()

        self._attempts_sock.connected.connect(on_connected)
        self._attempts_sock.readyRead.connect(on_ready_read)
        self._attempts_sock.errorOccurred.connect(lambda error: None)
        self._attempts_sock.connectToHost(host.strip(), port)


def get_resource_path(relative_path):
    """Получает абсолютный путь к ресурсу, работает для обычного запуска и для Nuitka/PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Для Nuitka
    base_path = os.path.dirname(os.path.abspath(__file__))
    # Если мы в папке client/, ищем в корне проекта
    potential_path = os.path.join(base_path, "..", relative_path)
    if os.path.exists(potential_path):
        return os.path.abspath(potential_path)
    return os.path.abspath(os.path.join(base_path, relative_path))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("TTGTiSO-Test — Студент")
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
            "/opt/test_system_student/icon.png"
        ]
        for path in icon_candidates:
            if os.path.exists(path):
                app.setWindowIcon(QIcon(path))
                break

    # Глобально отключаем системный прокси для всех сокетов
    QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.NoProxy))

    client = StudentClient()

    from ui_client import StudentWindow
    window = StudentWindow(client)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
