"""
Тесты универсального стилизованного файлового менеджера StyledFileDialog.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

try:
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
except ImportError:
    pytest.skip("QtWidgets not available", allow_module_level=True)

from server.ui_dialogs import DirectoryChooserDialog, StyledFileDialog


def test_styled_file_dialog_filter_setup():
    dlg = StyledFileDialog(
        title="Тест",
        filter_str="Файлы Excel (*.xlsx);;CSV-файлы (*.csv);;Все файлы (*.*)",
        mode=StyledFileDialog.Mode.SAVE_FILE,
    )
    assert len(dlg.parsed_filters) == 3
    assert dlg.parsed_filters[0][0] == "Файлы Excel (*.xlsx)"
    assert dlg.parsed_filters[0][1] == ["*.xlsx"]
    assert dlg.parsed_filters[1][0] == "CSV-файлы (*.csv)"
    assert dlg.parsed_filters[1][1] == ["*.csv"]
    assert dlg.parsed_filters[2][0] == "Все файлы (*.*)"
    assert dlg.parsed_filters[2][1] == ["*.*"]


def test_styled_file_dialog_default_filename(tmp_path):
    dlg = StyledFileDialog(
        title="Экспорт",
        initial_path=str(tmp_path),
        filter_str="Файлы Excel (*.xlsx)",
        mode=StyledFileDialog.Mode.SAVE_FILE,
        default_filename="Результаты_2026-08-30.xlsx",
    )
    assert dlg.file_name_edit.text() == "Результаты_2026-08-30.xlsx"
    assert os.path.exists(dlg.current_dir)


def test_styled_file_dialog_directory_mode(tmp_path):
    dlg = DirectoryChooserDialog(initial_path=str(tmp_path))
    assert dlg.mode == StyledFileDialog.Mode.CHOOSE_DIR
    assert dlg.current_dir == str(tmp_path)
    assert not hasattr(dlg, "file_name_edit")


def test_styled_file_dialog_nested_file_selection(tmp_path):
    sub = tmp_path / "Рабочий стол" / "Резервная копия"
    sub.mkdir(parents=True, exist_ok=True)
    sample_log = sub / "Бэкап_123123_43434.log"
    sample_log.write_text("test log", encoding="utf-8")

    dlg = StyledFileDialog(
        title="Открыть лог",
        initial_path=str(tmp_path),
        filter_str="Лог-файлы (*.log)",
        mode=StyledFileDialog.Mode.OPEN_FILE,
    )

    idx = dlg.model.index(str(sample_log))
    dlg._on_tree_clicked(idx)

    assert dlg.current_dir == str(sub)
    assert dlg.selected_file == str(sample_log)
    assert dlg.file_name_edit.text() == "Бэкап_123123_43434.log"

    dlg._accept_selection()
    assert dlg.selected_file == str(sample_log)

