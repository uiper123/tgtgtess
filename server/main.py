"""
server/main.py — Точка входа сервера преподавателя (TCP-сервер + GUI).

Запускает PySide6-приложение с интерфейсом преподавателя.
TCP-сервер работает через QTcpServer, принимая JSON-пакеты от студентов.
"""

import sys
import os
import json
import csv
import struct
import random
from functools import partial
from datetime import datetime
from typing import Dict, List, Any, Optional

from PySide6.QtCore import Qt, QObject, Signal, Slot, QByteArray
from PySide6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress
from PySide6.QtWidgets import QApplication

# Добавляем корень проекта в sys.path для импорта shared
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.parser import parse_test_file, questions_to_network_payload, calculate_score
from shared.protocol import pack_message

try:
    from .storage import project_root, results_path, safe_test_filename
except ImportError:
    from storage import project_root, results_path, safe_test_filename


# ---------------------------------------------------------------------------

MAX_MESSAGE_SIZE = 50 * 1024 * 1024


class ConnectedStudent:
    """Данные о подключённом студенте."""
    __slots__ = ('socket', 'name', 'group', 'buffer', 'finished', 'score', 'active', 'answers', 'questions', 'cheat_warnings', 'connect_time')

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

    def start_exam(self, group: str, duration: int, questions: list, title: str, section: str, test_name: str, port: int = None, partial_multiple: bool = True, random_order: bool = False, max_attempts: int = 1, questions_limit: int = None):
        """Запускает экзамен для конкретной группы: открывает TCP-порт и добавляет в список активных."""
        if not questions:
            self.server_error.emit("Сначала загрузите или выберите файл теста!")
            return

        group_key = group.strip().lower()
        self._active_exams[group_key] = {
            'group': group.strip(),
            'test_name': test_name,
            'questions': questions,
            'network_payload': questions_to_network_payload(questions),
            'duration': duration,
            'title': title,
            'section': section,
            'partial_multiple': partial_multiple,
            'random_order': random_order,
            'max_attempts': max(1, int(max_attempts)),
            'attempts': {},
            'questions_limit': questions_limit,
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
            
        # Если активных экзаменов больше нет, выключаем TCP-сервер
        if not self._active_exams:
            self._exam_active = False
            if self._tcp_server.isListening():
                self._tcp_server.close()
            self.log_message.emit("Все экзамены остановлены. Сервер отключен.")
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
        if self._tcp_server.isListening():
            self._tcp_server.close()
        self.log_message.emit("Все экзамены остановлены.")
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

    def _handle_connect(self, sock: QTcpSocket, packet: dict):
        """Обрабатывает запрос студента на подключение."""
        name = packet.get('name', '').strip()
        group = packet.get('group', '').strip()

        if not name or not group:
            response = {'status': 'error', 'message': 'empty_fields'}
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
        attempts_used = exam.setdefault('attempts', {}).get(student_key, 0)
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
        self._students[sock] = student
        self._monitor_data[(name, group)] = student

        questions_for_student = list(exam['questions'])
        limit = exam.get('questions_limit')
        if limit and limit < len(questions_for_student):
            questions_for_student = random.sample(questions_for_student, limit)
        elif exam.get('random_order'):
            questions_for_student = random.sample(questions_for_student, len(questions_for_student))

        student.questions = questions_for_student

        # Отправляем тест
        response = {
            'status': 'success',
            'questions': questions_to_network_payload(questions_for_student),
            'duration': exam['duration'],
            'title': exam['title'],
            'section': exam['section'],
            'test_name': exam.get('test_name', 'Тест')
        }
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
            elapsed = (datetime.now() - student.connect_time).total_seconds()
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

        if group_key in self._active_exams:
            attempts = self._active_exams[group_key].setdefault('attempts', {})
            student_key = name.strip().casefold()
            attempts[student_key] = attempts.get(student_key, 0) + 1

        result_entry = {
            'name': name,
            'group': group,
            'score': score,
            'answers': int_answers,
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
        import json
        path = results_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._all_results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message.emit(f"Ошибка записи истории результатов: {e}")

    def clear_all_results(self):
        self._all_results.clear()
        self._save_all_results_to_file()
        self.log_message.emit("Вся история результатов очищена.")


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
    from PySide6.QtGui import QIcon
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

    # Импортируем и создаём GUI
    from ui_server import ServerWindow
    window = ServerWindow(exam_server)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
