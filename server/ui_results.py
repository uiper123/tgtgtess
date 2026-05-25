import os
import json
from datetime import datetime
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox,
    QSizePolicy, QFrame, QTextEdit, QAbstractItemView,
    QScrollArea, QCheckBox, QComboBox, QGridLayout
)
from shared.parser import get_grade_details, questions_to_network_payload, parse_test_file

try:
    from .ui_dialogs import (
        StudentAnswersDialog, EditQuestionDialog, MonitoringDialog,
        DropZoneWidget, SelectTestFromRepoDialog
    )
except ImportError:
    from ui_dialogs import (
        StudentAnswersDialog, EditQuestionDialog, MonitoringDialog,
        DropZoneWidget, SelectTestFromRepoDialog
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
            "QFrame#filterCard { background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }"
        )
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 12, 12, 12)
        filter_layout.setSpacing(16)

        # Search Box layout
        search_lay = QVBoxLayout()
        search_lay.setSpacing(4)
        search_lbl = QLabel("Поиск")
        search_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; border: none; background: transparent;")
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
        group_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; border: none; background: transparent;")
        self.r_group_filter = QComboBox()
        self.r_group_filter.currentIndexChanged.connect(self._update_results_table)
        group_lay.addWidget(group_lbl)
        group_lay.addWidget(self.r_group_filter)
        filter_layout.addLayout(group_lay, 1)

        # Sort Filter layout
        sort_lay = QVBoxLayout()
        sort_lay.setSpacing(4)
        sort_lbl = QLabel("Сортировка")
        sort_lbl.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; border: none; background: transparent;")
        self.r_sort_filter = QComboBox()
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
        self.r_table = QTableWidget(0, 5)
        self.r_table.setHorizontalHeaderLabels(["Имя студента", "Группа", "Набранные баллы", "Процент", "Время сдачи"])
        self.r_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.r_table.setColumnWidth(0, 300)
        self.r_table.setColumnWidth(1, 120)
        self.r_table.setColumnWidth(2, 150)
        self.r_table.setColumnWidth(3, 120)
        self.r_table.setColumnWidth(4, 200)
        self.r_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.r_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.r_table.verticalHeader().setVisible(False)
        self.r_table.setShowGrid(True)
        self.r_table.setMinimumHeight(350)
        layout.addWidget(self.r_table)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Экспортировать отфильтрованные в CSV")
        export_btn.setProperty("class", "successBtn")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_manually)
        btn_row.addWidget(export_btn)
        
        import_log_btn = QPushButton("Импортировать лог студента (.log)")
        import_log_btn.setStyleSheet(
            "QPushButton { background-color: #8b5cf6; color: #ffffff; font-weight: bold; font-size: 13px; padding: 8px 16px; border: none; border-radius: 6px; }"
            "QPushButton:hover { background-color: #7c3aed; }"
        )
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
            results = [r for r in results if search_text in r.get('name', '').lower()]

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
            
            score_str = r.get('score', '0/0')
            self.r_table.setItem(row, 2, QTableWidgetItem(score_str))
            
            grade_text, grade_color = get_grade_details(score_str)
            grade_item = QTableWidgetItem(grade_text)
            grade_item.setForeground(QColor(grade_color))
            self.r_table.setItem(row, 3, grade_item)
            
            self.r_table.setItem(row, 4, QTableWidgetItem(r.get('timestamp', '')))

    def _export_manually(self):
        if not hasattr(self, 'filtered_results') or not self.filtered_results:
            QMessageBox.warning(self, "Предупреждение", "Нет результатов для экспорта!")
            return
        
        path, _ = self._get_save_file_name("Экспортировать отфильтрованные результаты", "results_filtered.csv", "CSV-файлы (*.csv)")
        if path:
            if not path.lower().endswith('.csv'):
                path += '.csv'
            import csv
            try:
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
                QMessageBox.information(self, "Успешно", f"Отфильтрованные результаты успешно сохранены:\n{path}")
            except IOError as exc:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать результаты: {exc}")

    def _import_student_log(self):
        log_path, _ = self._get_open_file_name("Выберите файл лога студента", "", "Лог-файлы (*.log)")
        if not log_path:
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
            test_name_in_log = log_json.get('test_name', '')
            
            # В логе лежат номера вопросов как строки (JSON keys), приводим к int
            int_answers = {}
            for k, v in student_answers.items():
                try:
                    int_answers[int(k)] = v
                except:
                    pass
            
            # 2. Пытаемся автоматически найти тест в репозитории
            questions = None
            if test_name_in_log:
                from .storage import test_path
                potential_path = test_path(test_name_in_log)
                if os.path.exists(potential_path):
                    try:
                        questions = parse_test_file(potential_path)
                    except:
                        pass
            
            if not questions:
                QMessageBox.information(self, "Выбор теста", 
                    f"Лог студента {student_name} загружен.\nАвтоматически найти тест '{test_name_in_log}' не удалось.\nВыберите файл теста (.txt) вручную.")
                
                manual_test_path, _ = self._get_open_file_name("Выберите файл теста для оценки", "", "Текстовые файлы (*.txt)")
                if not manual_test_path:
                    return
                questions = parse_test_file(manual_test_path)

            if not questions:
                raise ValueError("Файл теста пуст или неверного формата.")
            
            # 3. Рассчитываем и сохраняем
            from shared.parser import calculate_score
            score = calculate_score(questions, int_answers, partial_multiple=True)
            
            result_entry = {
                'name': student_name,
                'group': student_group,
                'score': score,
                'answers': int_answers,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " (Импорт)",
            }
            
            self.exam_server._all_results.append(result_entry)
            self.exam_server._save_all_results_to_file()
            self._update_results_table()
            
            QMessageBox.information(self, "Успешно", f"Результат студента {student_name} успешно импортирован!\nОценка: {score}")
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать лог: {e}")

    # ========================== 5. НАСТРОЙКИ СИСТЕМЫ ==========================
