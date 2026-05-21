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
from datetime import datetime
from typing import Dict, List, Any, Optional

from PySide6.QtCore import Qt, QObject, Signal, Slot, QByteArray
from PySide6.QtNetwork import QTcpServer, QTcpSocket, QHostAddress
from PySide6.QtWidgets import QApplication

# Добавляем корень проекта в sys.path для импорта shared
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.parser import parse_test_file, questions_to_network_payload, calculate_score


# ---------------------------------------------------------------------------
# Протокол: длина пакета (4 байта, big-endian) + JSON-данные (UTF-8)
# ---------------------------------------------------------------------------

def pack_message(data: dict) -> bytes:
    """Упаковывает словарь в сетевой пакет: [4 байта длины][JSON UTF-8]."""
    raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
    return struct.pack('!I', len(raw)) + raw


class ConnectedStudent:
    """Данные о подключённом студенте."""
    __slots__ = ('socket', 'name', 'group', 'buffer', 'finished', 'score', 'active', 'answers', 'questions')

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
    server_started = Signal(str, int)              # address, port
    server_error = Signal(str)                     # message
    log_message = Signal(str)                      # message

    DEFAULT_PORT = 9876

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tcp_server = QTcpServer(self)
        self._tcp_server.newConnection.connect(self._on_new_connection)

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

    # -- Внутренние обработчики сетевых событий --

    @Slot()
    def _on_new_connection(self):
        while self._tcp_server.hasPendingConnections():
            client_socket = self._tcp_server.nextPendingConnection()
            if client_socket is None:
                continue
            # Временно сохраняем сокет с пустым студентом, чтобы читать данные
            client_socket.readyRead.connect(lambda s=client_socket: self._on_data_ready(s))
            client_socket.disconnected.connect(lambda s=client_socket: self._on_disconnected(s))

    def _on_data_ready(self, sock: QTcpSocket):
        """Читает данные из сокета и обрабатывает JSON-пакеты."""
        student = self._students.get(sock)

        # Если студент ещё не зарегистрирован, создаём временный буфер
        if student is None:
            # Первый пакет — запрос на подключение
            buf = QByteArray()
        else:
            buf = student.buffer

        buf.append(sock.readAll())

        # Обрабатываем все полные пакеты в буфере
        while len(buf) >= 4:
            msg_len = struct.unpack('!I', buf[:4].data())[0]
            if len(buf) < 4 + msg_len:
                break  # неполный пакет, ждём ещё данных

            raw_json = buf[4:4 + msg_len].data().decode('utf-8')
            buf = buf[4 + msg_len:]

            try:
                packet = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                self.log_message.emit(f"Ошибка JSON от клиента: {exc}")
                continue

            self._handle_packet(sock, packet)

        # Сохраняем остаток буфера
        if student is not None:
            student.buffer = buf
        elif sock in self._students:
            self._students[sock].buffer = buf

    def _handle_packet(self, sock: QTcpSocket, packet: dict):
        """Обрабатывает один JSON-пакет от клиента."""
        action = packet.get('action')

        if action == 'connect':
            self._handle_connect(sock, packet)
        elif action == 'result':
            self._handle_result(sock, packet)
        elif action == 'get_active_group':
            self._handle_get_active_group(sock, packet)
        else:
            self.log_message.emit(f"Неизвестное действие: {action}")

    def _handle_get_active_group(self, sock: QTcpSocket, packet: dict):
        """Отправляет список активных академических групп."""
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
        }
        sock.write(pack_message(response))
        sock.flush()

        self.student_connected.emit(name, group)
        self.log_message.emit(f"Подключён: {name} ({group})")

    def _handle_result(self, sock: QTcpSocket, packet: dict):
        """Обрабатывает отправку результатов от студента."""
        student = self._students.get(sock)
        name = packet.get('name', '').strip()
        group = packet.get('group', '').strip()
        answers = packet.get('answers', {})

        # Конвертируем ключи ответов в int для сопоставления
        int_answers = {}
        for k, v in answers.items():
            try:
                int_answers[int(k)] = v
            except ValueError:
                pass

        # Точный подсчёт очков по ключам правильных ответов для конкретного теста
        group_key = group.lower()
        if student and getattr(student, 'questions', None):
            questions_to_use = student.questions
            if group_key in self._active_exams:
                exam = self._active_exams[group_key]
                partial_multiple = exam.get('partial_multiple', True)
            else:
                partial_multiple = True
        elif group_key in self._active_exams:
            exam = self._active_exams[group_key]
            questions_to_use = exam['questions']
            partial_multiple = exam.get('partial_multiple', True)
        else:
            questions_to_use = self._questions
            partial_multiple = True

        score = calculate_score(questions_to_use, int_answers, partial_multiple=partial_multiple)
        first_result_for_attempt = not student or not student.finished

        if student:
            student.finished = True
            student.score = score
            student.answers = int_answers

        # Также обновляем в мониторинге
        if (name, group) in self._monitor_data:
            self._monitor_data[(name, group)].finished = True
            self._monitor_data[(name, group)].score = score
            self._monitor_data[(name, group)].answers = int_answers

        if group_key in self._active_exams and first_result_for_attempt:
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
        self._save_all_results_to_file()

        # Отправляем подтверждение и точный результат клиенту
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
        student = self._students.pop(sock, None)
        if student:
            self.log_message.emit(f"Отключён: {student.name}")
            student.active = False
            # Обновляем в мониторинге
            if (student.name, student.group) in self._monitor_data:
                self._monitor_data[(student.name, student.group)].active = False
        sock.deleteLater()

    # -- Экспорт результатов --

    def _export_results_csv(self):
        """Сохраняет результаты текущего экзамена в CSV-файл."""
        if not self._results:
            self.log_message.emit("Нет результатов для экспорта.")
            return

        date_str = datetime.now().strftime('%Y-%m-%d_%H-%M')
        group_safe = self._allowed_group.replace(' ', '_').replace('/', '-')
        filename = f"Результаты_{group_safe}_{date_str}.csv"

        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'group', 'score', 'timestamp'])
                writer.writeheader()
                writer.writerows(self._results)
            self.log_message.emit(f"Результаты сохранены: {filename}")
        except IOError as exc:
            self.server_error.emit(f"Ошибка сохранения CSV: {exc}")

    # -- Персистентная история результатов --

    def _load_all_results_from_file(self):
        import json
        path = "results.json"
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._all_results = json.load(f)
                self.log_message.emit(f"Загружена история результатов: {len(self._all_results)} записей.")
            except Exception as e:
                self.log_message.emit(f"Ошибка чтения истории результатов: {e}")

    def _save_all_results_to_file(self):
        import json
        path = "results.json"
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._all_results, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_message.emit(f"Ошибка записи истории результатов: {e}")

    def clear_all_results(self):
        self._all_results.clear()
        self._save_all_results_to_file()
        self.log_message.emit("Вся история результатов очищена.")


def main():
    """Запуск приложения сервера преподавателя."""
    app = QApplication(sys.argv)
    app.setApplicationName("TTGTiSO-Test — Сервер")
    app.setOrganizationName("EduTest")

    # Установка иконки приложения
    from PySide6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(__file__), "..", "image.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # Создаём сервер экзаменов
    exam_server = ExamServer()

    # Импортируем и создаём GUI
    from ui_server import ServerWindow
    window = ServerWindow(exam_server)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
