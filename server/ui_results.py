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
        group_lbl = QLabel("Академическая группа")
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
        self.r_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.r_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.r_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.r_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.r_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.r_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.r_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.r_table.verticalHeader().setVisible(False)
        self.r_table.setShowGrid(False)
        self.r_table.setMinimumHeight(350)
        layout.addWidget(self.r_table)

        btn_row = QHBoxLayout()
        export_btn = QPushButton("Экспортировать отфильтрованные в CSV")
        export_btn.setProperty("class", "successBtn")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_manually)
        btn_row.addWidget(export_btn)
        
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

    # ========================== 5. НАСТРОЙКИ СИСТЕМЫ ==========================
