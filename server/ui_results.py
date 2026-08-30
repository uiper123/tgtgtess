import json
import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from shared.parser import get_grade_details, parse_test_file
from shared.widgets import StyledComboBox

try:
    from .ui_dialogs import (
        DropZoneWidget,
        EditQuestionDialog,
        MonitoringDialog,
        SelectTestFromRepoDialog,
        StudentAnswersDialog,
    )
except ImportError:
    from ui_dialogs import (
        StudentAnswersDialog,
    )

class ResultsMixin:
    def _build_results_page(self):
        self.results_page = QWidget()
        main_layout = QVBoxLayout(self.results_page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Создаем QScrollArea для удобной прокрутки результатов студентов на любых экранах
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        title = QLabel("Итоговые результаты студентов")
        title.setProperty("class", "sectionTitle")
        title.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(title)

        # Filters and Search Card Container (premium design alignment)
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_card.setStyleSheet(
            "QFrame#filterCard { background-color: #ffffff; border: 1px solid #e7e5e4; border-radius: 12px; padding: 12px; }"
        )
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(16)

        # Search Box layout
        search_lay = QVBoxLayout()
        search_lay.setSpacing(4)
        search_lbl = QLabel("Поиск")
        search_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #78716c; border: none; background: transparent;")
        self.r_search = QLineEdit()
        self.r_search.setPlaceholderText("🔍 Введите имя для поиска...")
        self.r_search.textChanged.connect(self._update_results_table)
        search_lay.addWidget(search_lbl)
        search_lay.addWidget(self.r_search)
        filter_layout.addLayout(search_lay, 2)

        # Group Filter layout
        group_lay = QVBoxLayout()
        group_lay.setSpacing(4)
        group_lbl = QLabel("Группа")
        group_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #78716c; border: none; background: transparent;")
        self.r_group_filter = StyledComboBox()
        self.r_group_filter.currentIndexChanged.connect(self._update_results_table)
        group_lay.addWidget(group_lbl)
        group_lay.addWidget(self.r_group_filter)
        filter_layout.addLayout(group_lay, 1)

        # Sort Filter layout
        sort_lay = QVBoxLayout()
        sort_lay.setSpacing(4)
        sort_lbl = QLabel("Сортировка")
        sort_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #78716c; border: none; background: transparent;")
        self.r_sort_filter = StyledComboBox()
        self.r_sort_filter.addItems([
            "По умолчанию",
            "Имя (А-Я)",
            "Имя (Я-А)",
            "Группа",
            "Процент (По убыванию)",
            "Процент (По возрастанию)"
        ])
        self.r_sort_filter.currentIndexChanged.connect(self._update_results_table)
        sort_lay.addWidget(sort_lbl)
        sort_lay.addWidget(self.r_sort_filter)
        filter_layout.addLayout(sort_lay, 1)

        layout.addWidget(filter_card)

        # Table of Results
        self.r_table = QTableWidget(0, 6)
        self.r_table.setHorizontalHeaderLabels(["Имя студента", "Группа", "Название теста", "Набранные баллы", "Процент", "Время сдачи"])
        self.r_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.r_table.setColumnWidth(0, 250)
        self.r_table.setColumnWidth(1, 100)
        self.r_table.setColumnWidth(2, 200)
        self.r_table.setColumnWidth(3, 190)
        self.r_table.setColumnWidth(4, 100)
        self.r_table.setColumnWidth(5, 180)
        self.r_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.r_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.r_table.verticalHeader().setVisible(False)
        self.r_table.verticalHeader().setDefaultSectionSize(44)
        self.r_table.setShowGrid(True)
        self.r_table.setMinimumHeight(350)
        self.r_table.cellDoubleClicked.connect(self._on_result_row_double_clicked)
        layout.addWidget(self.r_table)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Экспортировать в Excel (.xlsx)")
        export_btn.setProperty("class", "successBtn")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_manually)
        btn_row.addWidget(export_btn)

        import_log_btn = QPushButton("Импортировать лог студента (.log)")
        import_log_btn.setProperty("class", "secondaryBtn")
        import_log_btn.setCursor(Qt.PointingHandCursor)
        import_log_btn.clicked.connect(self._import_student_log)
        btn_row.addWidget(import_log_btn)

        clear_btn = QPushButton("Очистить всю историю результатов")
        clear_btn.setProperty("class", "dangerBtn")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_results_history)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)
        self.stacked_widget.addWidget(self.results_page)

    def _clear_results_history(self):
        reply = QMessageBox.question(
            self, "Очистить историю результатов",
            "Вы уверены, что хотите безвозвратно удалить всю сохраненную историю результатов студентов?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.exam_server.clear_all_results()
            self._update_results_table()
            QMessageBox.information(self, "Успешно", "История результатов успешно очищена.")

    def _refresh_group_filter_list(self):
        self.r_group_filter.blockSignals(True)
        current = self.r_group_filter.currentText()
        self.r_group_filter.clear()
        self.r_group_filter.addItem("Все группы")

        # Collect all unique groups
        groups = sorted(list(set(r.get('group', '') for r in self.exam_server.results if r.get('group'))))
        self.r_group_filter.addItems(groups)

        idx = self.r_group_filter.findText(current)
        if idx >= 0:
            self.r_group_filter.setCurrentIndex(idx)
        else:
            self.r_group_filter.setCurrentIndex(0)
        self.r_group_filter.blockSignals(False)

    def _update_results_table(self):
        self._refresh_group_filter_list()
        self.r_table.setRowCount(0)
        results = list(self.exam_server.results)

        # 1. Apply search filter
        search_text = self.r_search.text().strip().lower()
        if search_text:
            results = [r for r in results if
                search_text in r.get('name', '').lower() or
                search_text in r.get('group', '').lower() or
                search_text in r.get('test_name', '').lower()
            ]

        # 2. Apply group filter
        group_filter = self.r_group_filter.currentText()
        if group_filter and group_filter != "Все группы":
            results = [r for r in results if r.get('group') == group_filter]

        # 3. Apply sorting
        sort_type = self.r_sort_filter.currentText()
        if sort_type == "Имя (А-Я)":
            results.sort(key=lambda x: x.get('name', '').lower())
        elif sort_type == "Имя (Я-А)":
            results.sort(key=lambda x: x.get('name', '').lower(), reverse=True)
        elif sort_type == "Группа":
            results.sort(key=lambda x: x.get('group', '').lower())
        elif sort_type == "Процент (По убыванию)":
            def get_percent(res):
                try:
                    parts = res.get('score', '0/0').split('/')
                    return float(parts[0]) / float(parts[1]) if float(parts[1]) > 0 else 0
                except Exception:
                    return 0
            results.sort(key=get_percent, reverse=True)
        elif sort_type == "Процент (По возрастанию)":
            def get_percent(res):
                try:
                    parts = res.get('score', '0/0').split('/')
                    return float(parts[0]) / float(parts[1]) if float(parts[1]) > 0 else 0
                except Exception:
                    return 0
            results.sort(key=get_percent)

        self.filtered_results = results

        # 4. Fill the table
        for r in results:
            row = self.r_table.rowCount()
            self.r_table.insertRow(row)
            self.r_table.setItem(row, 0, QTableWidgetItem(r.get('name', '')))
            self.r_table.setItem(row, 1, QTableWidgetItem(r.get('group', '')))

            test_name = r.get('test_name', '')
            if not test_name:
                test_name = '—'
            self.r_table.setItem(row, 2, QTableWidgetItem(test_name))

            score_str = r.get('score', '0/0')
            self.r_table.setItem(row, 3, QTableWidgetItem(score_str))

            grade_text, grade_color = get_grade_details(score_str)
            grade_item = QTableWidgetItem(grade_text)
            grade_item.setForeground(QColor(grade_color))
            self.r_table.setItem(row, 4, grade_item)

            self.r_table.setItem(row, 5, QTableWidgetItem(r.get('timestamp', '')))

    def _on_result_row_action(self, row):
        # Delegate to the existing double-click handler which already has smart loading logic
        self._on_result_row_double_clicked(row, 0)

    def _export_manually(self):
        if not hasattr(self, 'filtered_results') or not self.filtered_results:
            QMessageBox.warning(self, "Предупреждение", "Нет результатов для экспорта!")
            return

        date_str = datetime.now().strftime('%Y-%m-%d')
        default_name = f"Результаты_{date_str}.xlsx"
        path, _ = self._get_save_file_name(
            "Экспортировать результаты в Excel",
            "",
            "Файлы Excel (*.xlsx);;CSV-файлы (*.csv);;Все файлы (*.*)",
            default_filename=default_name,
        )
        if path:
            if not path.lower().endswith('.xlsx') and not path.lower().endswith('.csv'):
                path += '.xlsx'

            current_group_filter = self.r_group_filter.currentText() if hasattr(self, 'r_group_filter') else ""
            if current_group_filter == "Все группы":
                current_group_filter = ""

            try:
                if path.lower().endswith('.xlsx'):
                    try:
                        from .export_excel import export_results_to_xlsx
                    except ImportError:
                        from export_excel import export_results_to_xlsx

                    export_results_to_xlsx(
                        self.filtered_results,
                        path,
                        title="Ведомость результатов тестирования",
                        group_name=current_group_filter,
                    )
                else:
                    import csv
                    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.DictWriter(f, fieldnames=['name', 'group', 'score', 'timestamp'])
                        writer.writeheader()
                        for r in self.filtered_results:
                            writer.writerow({
                                'name': r.get('name', ''),
                                'group': r.get('group', ''),
                                'score': r.get('score', ''),
                                'timestamp': r.get('timestamp', '')
                            })
                QMessageBox.information(self, "Успешно", f"Результаты успешно экспортированы:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать результаты: {exc}")

    def _import_student_log(self):
        log_path, _ = self._get_open_file_name(
            "Выберите файл лога студента",
            "",
            "Лог-файлы (*.log);;Все файлы (*.*)"
        )
        if not log_path or not os.path.exists(log_path):
            return

        try:
            # 1. Читаем и расшифровываем лог
            with open(log_path, 'rb') as f:
                encrypted_data = f.read()

            key = b'EduTestPro2025'
            decrypted = bytearray(len(encrypted_data))
            klen = len(key)
            for i, b in enumerate(encrypted_data):
                decrypted[i] = b ^ key[i % klen]

            log_json = json.loads(decrypted.decode('utf-8'))
            student_name = log_json.get('name', 'Неизвестный')
            student_group = log_json.get('group', 'Неизвестная')
            student_answers = log_json.get('answers', {})
            test_name = log_json.get('test_name', '') or log_json.get('test_title', '') or 'Тест'
            questions = log_json.get('questions', None)
            recorded_score = log_json.get('score', '')
            timestamp = log_json.get('completed_at') or log_json.get('timestamp') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # В логе лежат номера вопросов как строки (JSON keys), приводим к int
            int_answers = {}
            for k, v in student_answers.items():
                try:
                    int_answers[int(k)] = v if isinstance(v, list) else [str(v)]
                except (TypeError, ValueError):
                    pass

            final_score = None

            # 2. Если в логе есть вопросы — рассчитываем точную оценку (или используем сохраненную)
            if questions and isinstance(questions, list) and len(questions) > 0:
                try:
                    from shared.parser import calculate_score
                    final_score = calculate_score(questions, int_answers, partial_multiple=True)
                except Exception:
                    final_score = None

            # Если оценка не рассчиталась, но была сохранена в логе
            if not final_score and recorded_score and "/" in str(recorded_score):
                final_score = str(recorded_score)

            # 3. Если вопросов в логе нет (старый формат v1), ищем тест в репозитории автоматически
            if not questions or not final_score:
                try:
                    from .storage import test_path, tests_dir
                except ImportError:
                    from storage import test_path, tests_dir

                found_path = None
                if test_name:
                    potential_path = test_path(test_name)
                    if os.path.exists(potential_path):
                        found_path = potential_path

                # Рекурсивный поиск по всем подпапкам репозитория
                if not found_path:
                    d = tests_dir()
                    if d.exists():
                        for match in d.rglob("*.txt"):
                            if match.stem == test_name or match.stem.strip() == test_name:
                                found_path = match
                                break
                        if not found_path:
                            for match in d.rglob("*.json"):
                                if match.stem == test_name or match.stem.strip() == test_name:
                                    found_path = match
                                    break

                if found_path:
                    try:
                        if str(found_path).lower().endswith('.json'):
                            with open(found_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                questions = data.get("questions", [])
                        else:
                            questions = parse_test_file(str(found_path))

                        if questions:
                            from shared.parser import calculate_score
                            final_score = calculate_score(questions, int_answers, partial_multiple=True)
                    except Exception:
                        pass

            # Если всё ещё нет оценки, используем количество ответов
            if not final_score:
                if recorded_score:
                    final_score = str(recorded_score)
                else:
                    final_score = f"{len(int_answers)}/{len(questions) if questions else len(int_answers)}"

            # 4. Сохраняем результат
            result_entry = {
                'name': student_name,
                'group': student_group,
                'score': final_score,
                'answers': int_answers,
                'test_name': test_name,
                'timestamp': str(timestamp) + ("" if "Импорт" in str(timestamp) else " (Импорт)"),
            }
            if questions:
                result_entry['questions'] = questions

            self.exam_server._all_results.append(result_entry)
            self.exam_server._results.append(result_entry)
            self.exam_server._save_all_results_to_file()
            self._update_results_table()

            # Красивое уведомление о успешном импорте
            percent_str, _ = get_grade_details(final_score)
            QMessageBox.information(
                self,
                "Импорт завершён",
                f"Результат студента успешно импортирован!\n\n"
                f"👤 Студент: {student_name}\n"
                f"👥 Группа: {student_group}\n"
                f"📝 Тест: {test_name}\n"
                f"📊 Оценка: {final_score} ({percent_str})"
            )

        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать лог:\n{e}")

    def _on_result_row_double_clicked(self, row, col):
        try:
            if not hasattr(self, 'filtered_results') or row < 0 or row >= len(self.filtered_results):
                return

            result_entry = self.filtered_results[row]

            # 1. Пытаемся получить вопросы для этого студента
            questions = result_entry.get('questions')
            group = result_entry.get('group', '')

            # Если в самой записи вопросов нет, ищем в активных сессиях для этой группы
            if not questions and group:
                active_exam = self.exam_server._active_exams.get(group.lower())
                if active_exam:
                    questions = active_exam.get('questions')

            # Если активной сессии нет, пробуем найти тест по test_name или group в репозитории
            if not questions:
                try:
                    from .storage import test_path, tests_dir
                except ImportError:
                    from storage import test_path, tests_dir

                test_names_to_try = []
                if result_entry.get('test_name'):
                    test_names_to_try.append(result_entry['test_name'])
                if group:
                    test_names_to_try.append(group)

                for t_name in test_names_to_try:
                    json_path = test_path(t_name)
                    txt_path = json_path.with_suffix('.txt')

                    found_path = None
                    if os.path.exists(json_path):
                        found_path = json_path
                    elif os.path.exists(txt_path):
                        found_path = txt_path

                    # Рекурсивный поиск в папке тестов
                    if not found_path:
                        d = tests_dir()
                        if d.exists():
                            for match in d.rglob("*.txt"):
                                if match.stem == t_name or match.stem.strip() == t_name:
                                    found_path = match
                                    break
                            if not found_path:
                                for match in d.rglob("*.json"):
                                    if match.stem == t_name or match.stem.strip() == t_name:
                                        found_path = match
                                        break

                    if found_path:
                        try:
                            if str(found_path).lower().endswith('.json'):
                                with open(found_path, 'r', encoding='utf-8') as f:
                                    data = json.load(f)
                                    questions = data.get("questions", [])
                            else:
                                questions = parse_test_file(str(found_path))

                            if questions:
                                break
                        except Exception as e:
                            print(f"Failed to load test: {e}")
                            pass

            # Если все еще нет вопросов, используем StyledFileDialog для выбора файла теста
            if not questions:
                try:
                    from .storage import tests_dir
                    from .ui_dialogs import StyledFileDialog
                except ImportError:
                    from storage import tests_dir
                    from ui_dialogs import StyledFileDialog

                manual_test_path, _ = StyledFileDialog.get_open_file_name(
                    self,
                    f"Выберите файл теста для студента '{result_entry.get('name')}'",
                    str(tests_dir()),
                    "Файлы тестов (*.txt *.json);;Все файлы (*.*)"
                )
                if not manual_test_path or not os.path.exists(manual_test_path):
                    return
                try:
                    if manual_test_path.lower().endswith('.json'):
                        with open(manual_test_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            questions = data.get("questions", [])
                    else:
                        questions = parse_test_file(manual_test_path)
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл теста: {e}")
                    return

            if not questions:
                QMessageBox.warning(self, "Внимание", "Не удалось загрузить вопросы теста.")
                return

            # 2. Создаем псевдо-объект студента для StudentAnswersDialog
            # Приводим все ключи ответов к числовому и строковому виду
            answers_raw = result_entry.get('answers', {})
            answers_normalized = {}
            for k, v in answers_raw.items():
                answers_normalized[k] = v
                try:
                    answers_normalized[int(k)] = v
                except:
                    pass
                try:
                    answers_normalized[str(k)] = v
                except:
                    pass

            class PseudoStudent:
                def __init__(self, name, group, answers):
                    self.name = name
                    self.group = group
                    self.answers = answers

            student = PseudoStudent(
                name=result_entry.get('name', 'Неизвестный'),
                group=result_entry.get('group', 'Неизвестная'),
                answers=answers_normalized
            )

            # 3. Открываем диалог с ответами
            dialog = StudentAnswersDialog(student, questions, self)
            dialog.exec()

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при показе ответов:\n{e}\n\nTraceback:\n{tb}")

    # ========================== 5. НАСТРОЙКИ СИСТЕМЫ ==========================
