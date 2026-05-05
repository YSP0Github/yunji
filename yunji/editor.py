# editor
import argparse
import sys
import os
from pathlib import Path
try:
    import chardet
except ImportError:  # chardet is optional for UTF-8-only usage/tests.
    chardet = None
import platform
import subprocess

from PyQt5.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox,
                             QLabel, QColorDialog, QVBoxLayout, QWidget,
                             QFontDialog, QHBoxLayout, QPushButton, QAction,
                             QCheckBox, QStatusBar, QPlainTextEdit)
from PyQt5.QtGui import (QIcon, QFont, QTextCharFormat, QTextCursor,
                         QPalette, QColor, QPixmap)
from PyQt5.QtCore import Qt, QSize

try:
    from .text_editor import TextEditor
    from .find_replace import FindReplaceDialog
    from .file_io import read_text_file_with_fallback, convert_size
    from .find_service import (find_wrapped, replace_all, collect_matches,
                               determine_current_match, build_find_flags)
    from .syntax_highlighter import create_highlighter, language_for_path
    from .plugin_manager import PluginManager
    from . import __version__
except ImportError:  # Support running this file directly: python yunji/editor.py
    from text_editor import TextEditor
    from find_replace import FindReplaceDialog
    from file_io import read_text_file_with_fallback, convert_size
    from find_service import (find_wrapped, replace_all, collect_matches,
                              determine_current_match, build_find_flags)
    from syntax_highlighter import create_highlighter, language_for_path
    from plugin_manager import PluginManager
    __version__ = "0.4.0"


class YunjiEditor(QMainWindow):
    def __init__(self, filename=None, plugin_dirs=None, load_plugins=True):
        super().__init__()
        self.file_path = None
        self.current_directory = None
        self.temp_file = None
        self.child_windows = []
        self.is_saved = True
        self.encoding = 'utf-8'
        self.find_cache = {"key": None, "matches": []}
        self.syntax_highlighting_enabled = True
        self.syntax_highlighter = None
        self.plugin_manager = None

        self.init_ui()
        self.text_edit.textChanged.connect(self.on_text_changed)
        if filename:
            self.open_path(filename)
        if load_plugins:
            self.load_plugins(plugin_dirs=plugin_dirs, show_message=False)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(5, 0, 5, 0)

        self._create_header(layout)
        self._create_status_bar()
        self._create_editor(layout)
        icon_paths = self._resolve_icon_paths()
        actions = self._create_actions(icon_paths)
        self._create_menus(actions)
        self._create_settings_button()
        self._apply_window_settings(icon_paths["editor"])
        self.show()

    def _create_header(self, layout):
        background_widget = QWidget()
        background_widget.setStyleSheet("QWidget { background-color: #99CCCC; }")
        background_widget.setFixedHeight(1)
        layout.addWidget(background_widget)

        self.filename_label = QLabel("  ")
        self.filename_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.filename_label.setFixedHeight(20)
        self.filename_label.setContentsMargins(5, 0, 0, 0)
        self.filename_label.setStyleSheet("QLabel { background-color: #A4DDD3; color: #996600; }")
        self.filename_label.setFont(QFont("Consolas", 12))
        layout.addWidget(self.filename_label, alignment=Qt.AlignLeft)

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.status_label_filepath = QLabel(os.path.dirname(os.path.realpath(__file__)))
        self.status_label_filepath.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.status_label_filepath.setFixedHeight(15)
        self.status_label_filepath.setContentsMargins(5, 0, 0, 0)
        self.status_label_filepath.setStyleSheet("QLabel { background-color: #A4DDD3; color: #000000; }")
        self.status_label_filepath.setFont(QFont("Consolas", 10))

        self.status_label_line = QLabel("行: 1 ;  列: 1")
        self.status_label_line.setContentsMargins(10, 0, 10, 0)
        self.status_label_doc = QLabel("文档状态: 未修改")
        self.status_label_doc.setContentsMargins(10, 0, 10, 0)
        self.status_label_zoom = QLabel("100%")
        self.status_label_zoom.setContentsMargins(10, 0, 10, 0)
        self.status_label_encoding = QLabel("UTF-8")
        self.status_label_encoding.setContentsMargins(10, 0, 10, 0)
        self.status_label_file_size = QLabel("文件大小: 0 B")
        self.status_label_file_size.setContentsMargins(10, 0, 10, 0)

        self.status_label_os_info = QLabel(self._get_os_line_ending_info())
        self.status_label_os_info.setContentsMargins(10, 0, 10, 0)
        self.status_label_insert_mode = QLabel("INS")
        self.status_label_insert_mode.setContentsMargins(10, 0, 10, 0)

        self.status_bar.addWidget(self.status_label_filepath, 3)
        self.status_bar.addWidget(self.status_label_line, 1)
        self.status_bar.addWidget(self.status_label_insert_mode, 1)
        self.status_bar.addWidget(self.status_label_zoom, 1)
        self.status_bar.addWidget(self.status_label_encoding, 1)
        self.status_bar.addWidget(self.status_label_file_size, 1)
        self.status_bar.addPermanentWidget(self.status_label_os_info, 1)
        self.status_bar.addPermanentWidget(self.status_label_doc, 1)

    def _get_os_line_ending_info(self):
        os_info = platform.system()
        if os_info == "Windows":
            line_ending_info = "(CRLF)"
        elif os_info in ["Linux", "Darwin"]:
            line_ending_info = "(LF)"
        else:
            line_ending_info = "未知"
        return f"{os_info} {line_ending_info}"

    def _create_editor(self, layout):
        self.text_edit = TextEditor(parent=self)
        palette = self.text_edit.palette()
        palette.setColor(QPalette.Highlight, QColor("#A4DDD3"))
        self.text_edit.setPalette(palette)
        self.text_edit.setStyleSheet("QPlainTextEdit { selection-background-color: #A4DDD3; }")
        layout.addWidget(self.text_edit)
        self.update_insert_overwrite_mode()

    def _resolve_icon_paths(self):
        icon_base_path = os.path.join(os.path.dirname(__file__), "images")
        self.setting_path = os.path.join(icon_base_path, 'setting.png')
        return {
            "open": os.path.join(icon_base_path, 'open.png'),
            "save": os.path.join(icon_base_path, 'save.png'),
            "save_as": os.path.join(icon_base_path, 'save_as.png'),
            "editor": os.path.join(icon_base_path, 'editor.png'),
            "add": os.path.join(icon_base_path, 'add.png'),
            "setting": self.setting_path,
        }

    def _create_action(self, text, slot, shortcut=None, icon=None, checkable=False, checked=False):
        action = QAction(QIcon(icon), text, self) if icon else QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        if checkable:
            action.setCheckable(True)
            action.setChecked(checked)
        action.triggered.connect(slot)
        return action

    def _create_transparent_icon(self):
        transparent_pixmap = QPixmap(16, 16)
        transparent_pixmap.fill(Qt.transparent)
        return QIcon(transparent_pixmap)

    def _create_actions(self, icon_paths):
        transparent_icon = self._create_transparent_icon()
        self.show_line_numbers_action = self._create_action(
            '显示行号', self.toggle_line_numbers, checkable=True, checked=False
        )
        auto_wrap_action = self._create_action(
            '自动换行', self.toggle_auto_wrap, checkable=True, checked=True
        )
        self.syntax_highlighting_action = self._create_action(
            '语法高亮', self.toggle_syntax_highlighting, checkable=True, checked=True
        )

        actions = {
            "new_file": self._create_action('新建文件', self.new_file, 'Ctrl+N', icon_paths["add"]),
            "new_window": self._create_action('新建窗口', self.new_window, 'Ctrl+Shift+N', icon_paths["add"]),
            "open": self._create_action('打开', self.open_file_dialog, 'Ctrl+O', icon_paths["open"]),
            "save": self._create_action('保存', self.save_file, 'Ctrl+S', icon_paths["save"]),
            "save_as": self._create_action('另存为', self.save_file_as, 'Ctrl+Shift+S', icon_paths["save_as"]),
            "undo": self._create_action('撤销', self.text_edit.undo, 'Ctrl+Z'),
            "redo": self._create_action('重做', self.text_edit.redo, 'Ctrl+Y'),
            "cut": self._create_action('剪切', self.text_edit.cut, 'Ctrl+X'),
            "copy": self._create_action('复制', self.text_edit.copy, 'Ctrl+C'),
            "paste": self._create_action('粘贴', self.text_edit.paste, 'Ctrl+V'),
            "find": self._create_action('查找', self.find_text, 'Ctrl+F'),
            "replace": self._create_action('替换', self.replace_text, 'Ctrl+H'),
            "bold": self._create_action('加粗', self.bold_text, 'Ctrl+B'),
            "italic": self._create_action('斜体', self.italic_text, 'Ctrl+I'),
            "text_color": self._create_action('正文颜色', self.set_text_color),
            "line_number_color": self._create_action('行号颜色', self.set_line_number_color),
            "line_numbers": self.show_line_numbers_action,
            "auto_wrap": auto_wrap_action,
            "syntax_highlighting": self.syntax_highlighting_action,
            "reload_plugins": self._create_action('重新加载插件', self.reload_plugins),
            "plugin_info": self._create_action('插件信息', self.show_plugin_info),
            "run_python": self._create_action('运行当前 Python 文件', self.run_current_python_file, 'F5'),
        }
        actions["text_color"].setIcon(transparent_icon)
        actions["line_number_color"].setIcon(transparent_icon)
        return actions

    def _create_menus(self, actions):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('文件')
        for key in ["new_file", "new_window", "open", "save", "save_as"]:
            file_menu.addAction(actions[key])

        edit_menu = menubar.addMenu('编辑')
        for key in ["undo", "redo", "cut", "copy", "paste", "find", "replace"]:
            edit_menu.addAction(actions[key])

        format_menu = menubar.addMenu('格式')
        for key in ["bold", "italic"]:
            format_menu.addAction(actions[key])

        view_menu = menubar.addMenu('视图')
        for key in ["text_color", "line_number_color", "line_numbers", "auto_wrap", "syntax_highlighting"]:
            view_menu.addAction(actions[key])

        tool_menu = menubar.addMenu('工具')
        tool_menu.addAction(actions["run_python"])

        plugin_menu = menubar.addMenu('插件')
        for key in ["reload_plugins", "plugin_info"]:
            plugin_menu.addAction(actions[key])

    def _create_settings_button(self):
        widget = QWidget(self)
        hbox = QHBoxLayout(widget)
        hbox.setContentsMargins(0, 10, 15, 0)

        setting_button = QPushButton(QIcon(self.setting_path), '')
        setting_button.setIconSize(QSize(20, 20))
        setting_button.setToolTip('设置')
        setting_button.clicked.connect(self.open_settings_dialog)
        setting_button.setStyleSheet(
            "QPushButton { width: 18px; height: 18px; background-color: #A4DDD3; border: none }"
        )
        setting_button.setCursor(Qt.PointingHandCursor)

        hbox.addWidget(setting_button, alignment=Qt.AlignRight)
        widget.setLayout(hbox)
        self.menuBar().setCornerWidget(widget, Qt.TopRightCorner)

    def _apply_window_settings(self, editor_icon_path):
        self.setGeometry(200, 100, 1000, 900)
        self.setWindowTitle('云记')
        self.setWindowIcon(QIcon(editor_icon_path))
        self.setStyleSheet("""
            QMainWindow {
                background-color: #A4DDD3;
            }
            QPlainTextEdit {
                background-color: #ffffff;
                padding: 0px;
                border: 1px solid #ccc;
                border-radius: 5px;
                margin: 0px;
            }
            QMenuBar {
                background-color: #A4DDD3;
                font: 16px;
                padding: 0px;
            }
            QMenuBar::item {
                padding: 8px 10px;
                background: transparent;
                border-radius: 5px;
            }
            QMenuBar::item:selected {
                background: #ABD7EC;
                color: white;
            }
            QMenu {
                background-color: #A4DDD3;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            QMenu::item {
                padding: 8px 10px;
                background: transparent;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #A4DDD3;
                color: white;
            }
        """)

    def apply_syntax_highlighting(self, file_path=None):
        self.syntax_highlighter = None
        if not self.syntax_highlighting_enabled:
            return
        language = language_for_path(file_path)
        self.syntax_highlighter = create_highlighter(self.text_edit.document(), language)
        if self.syntax_highlighter:
            self.syntax_highlighter.rehighlight()

    def toggle_syntax_highlighting(self, checked):
        self.syntax_highlighting_enabled = checked
        self.apply_syntax_highlighting(self.file_path)

    def load_plugins(self, plugin_dirs=None, show_message=True):
        self.plugin_manager = PluginManager(self, plugin_dirs=plugin_dirs)
        self.plugin_manager.load_all()
        loaded, errors = self.plugin_manager.summary()
        if show_message:
            QMessageBox.information(self, '插件', f'已加载 {loaded} 个插件，失败 {errors} 个。')
        return loaded, errors

    def reload_plugins(self):
        return self.load_plugins(show_message=True)

    def show_plugin_info(self):
        if not self.plugin_manager:
            QMessageBox.information(self, '插件', '插件系统尚未加载。')
            return
        loaded, errors = self.plugin_manager.summary()
        dirs = '\n'.join(str(path) for path in self.plugin_manager.plugin_dirs)
        message = f'已加载插件: {loaded}\n加载失败: {errors}\n\n插件目录:\n{dirs}'
        if self.plugin_manager.errors:
            details = '\n'.join(f'{path}: {exc}' for path, exc in self.plugin_manager.errors)
            message += f'\n\n错误:\n{details}'
        QMessageBox.information(self, '插件信息', message)

    def wheelEvent(self, event):
        self.text_edit.wheelEvent(event)

    FILE_FILTERS = (
        "Python 文件 (*.py *.pyw);;"
        "文本文件 (*.txt *.md *.rst *.log);;"
        "JSON 文件 (*.json);;"
        "配置文件 (*.ini *.cfg *.toml *.yaml *.yml);;"
        "所有文件 (*)"
    )

    def open_file_dialog(self):
        try:
            file_path, _ = QFileDialog.getOpenFileName(self, '打开文件', '', self.FILE_FILTERS)
            if file_path:
                self.open_file(file_path)
        except Exception as exc:
            self.show_error_dialog('打开文件', f'无法打开文件对话框: {exc}')

    def open_path(self, path):
        path = os.path.abspath(os.fspath(path))
        if os.path.isdir(path):
            self.open_directory(path)
        else:
            self.open_file(path)

    def open_directory(self, directory_path):
        self.current_directory = os.path.abspath(directory_path)
        self.file_path = None
        self.filename_label.setText(os.path.basename(self.current_directory) or self.current_directory)
        self.status_label_filepath.setText(f'打开目录: {self.current_directory}')
        self.status_label_doc.setText('文档状态: 未修改')
        self.status_label_file_size.setText('文件大小: N/A')
        self.text_edit.clear()
        self.text_edit.document().setModified(False)
        self.is_saved = True
        self.apply_syntax_highlighting(None)

    def open_dropped_paths(self, paths):
        if not paths:
            return
        self.open_path(paths[0])
        for path in paths[1:]:
            new_window = YunjiEditor(load_plugins=False)
            new_window.open_path(path)
            self.child_windows.append(new_window)
            new_window.show()

    def open_file(self, file_path):
        if not file_path:
            return
        try:
            content, detected_encoding = self._read_file_with_fallback(file_path)
            self.file_path = file_path
            self.encoding = detected_encoding
            self.text_edit.blockSignals(True)
            try:
                self.text_edit.setPlainText(content)
            finally:
                self.text_edit.blockSignals(False)
            self.text_edit.document().setModified(False)
            self.filename_label.setText(os.path.basename(file_path))
            self.status_label_filepath.setText(f'打开文件: {file_path}')
            self.status_label_doc.setText("文档状态: 已打开")
            self.status_label_encoding.setText(self.encoding)
            self.update_file_size()
            self.is_saved = True
            self.reset_find_cache()
            self.update_cursor_position_after_open()
            self.apply_syntax_highlighting(file_path)
        except FileNotFoundError:
            QMessageBox.critical(self, "文件错误", f"文件 '{os.path.basename(file_path)}' 不存在.")
            self.clear_text_edit()
        except Exception as exc:
            self.show_error_dialog("打开文件", f"无法打开文件 '{os.path.basename(file_path)}': {exc}")
            self.clear_text_edit()

    def clear_text_edit(self):
        self.text_edit.clear()
        self.file_path = None
        self.current_directory = None
        self.filename_label.setText("  ")
        self.status_label_filepath.setText("当前路径: ")
        self.status_label_line.setText("行: 1 ;  列: 1")
        self.status_label_doc.setText("文档状态: 未修改")
        self.status_label_file_size.setText("文件大小: N/A")
        self.encoding = 'utf-8'
        self.status_label_encoding.setText("UTF-8")
        self.is_saved = True
        self.text_edit.document().setModified(False)
        self.reset_find_cache()
        self.apply_syntax_highlighting(None)

    def update_cursor_position_after_open(self):
        cursor = self.text_edit.textCursor()
        cursor.movePosition(QTextCursor.Start)
        self.text_edit.setTextCursor(cursor)
        self.status_label_line.setText("行: 1 ;  列: 1")

    def save_file(self):
        if not self.file_path:
            return self.save_file_as()
        try:
            with open(self.file_path, 'w', encoding=self.encoding or 'utf-8', newline='') as file:
                file.write(self.text_edit.toPlainText())
            self.filename_label.setText(os.path.basename(self.file_path))
            self.status_label_filepath.setText(f'保存文件: {self.file_path}')
            self.status_label_doc.setText("文档状态: 已保存")
            self.is_saved = True
            self.text_edit.document().setModified(False)
            self.update_file_size()
            self.apply_syntax_highlighting(self.file_path)
            return True
        except Exception as exc:
            self.show_error_dialog('保存文件', f'保存失败: {exc}')
            return False

    def save_file_as(self):
        try:
            file_path, selected_filter = QFileDialog.getSaveFileName(self, '另存为', '', self.FILE_FILTERS)
            if file_path:
                self.file_path = self._ensure_extension_for_filter(file_path, selected_filter)
                return self.save_file()
            return False
        except Exception as exc:
            self.show_error_dialog('另存为', f'无法另存文件: {exc}')
            return False

    def _ensure_extension_for_filter(self, file_path, selected_filter):
        root, ext = os.path.splitext(file_path)
        if ext:
            return file_path
        if selected_filter.startswith("Python 文件"):
            return file_path + ".py"
        if selected_filter.startswith("文本文件"):
            return file_path + ".txt"
        if selected_filter.startswith("JSON 文件"):
            return file_path + ".json"
        if selected_filter.startswith("配置文件"):
            return file_path + ".toml"
        return file_path

    def maybe_save_current_document(self):
        if self.is_saved or not self.text_edit.document().isModified():
            return True
        reply = QMessageBox.question(
            self,
            '保存更改',
            '当前文件有未保存的修改，是否保存？',
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Save:
            return self.save_file()
        if reply == QMessageBox.Cancel:
            return False
        return True

    def new_file(self):
        if not self.maybe_save_current_document():
            return False
        self.clear_text_edit()
        self.filename_label.setText("未命名")
        self.status_label_filepath.setText("新建文件")
        self.status_label_doc.setText("文档状态: 未修改")
        return True

    def new_window(self):
        try:
            new_window = YunjiEditor()
            self.child_windows.append(new_window)
            new_window.show()
        except Exception as exc:
            self.show_error_dialog('新建窗口', f'无法打开新的编辑窗口: {exc}')

    def find_text(self):
        try:
            if hasattr(self, 'find_dialog') and self.find_dialog.isVisible():
                self.find_dialog.close()
            selected_text = self.text_edit.textCursor().selectedText()
            self.find_dialog = FindReplaceDialog(self, initial_text=selected_text)
            self.find_dialog.find_button.clicked.connect(self.find_next_text)
            self.find_dialog.show()
            self.update_result_label(force_recount=True)
        except Exception as exc:
            self.show_error_dialog('查找', f'无法打开查找窗口: {exc}')

    def replace_text(self):
        try:
            if hasattr(self, 'find_dialog') and self.find_dialog.isVisible():
                self.find_dialog.close()
            selected_text = self.text_edit.textCursor().selectedText()
            self.find_dialog = FindReplaceDialog(self, True, initial_text=selected_text)
            self.find_dialog.find_button.clicked.connect(self.find_next_text)
            self.find_dialog.replace_button.clicked.connect(self.replace_next_text)
            self.find_dialog.replace_all_button.clicked.connect(self.replace_all_text)
            self.find_dialog.show()
            self.update_result_label(force_recount=True)
        except Exception as exc:
            self.show_error_dialog('替换', f'无法打开替换窗口: {exc}')

    def find_next_text(self):
        if not hasattr(self, 'find_dialog'):
            return
        try:
            find_str, _, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
            if not find_str:
                self.update_result_label(force_recount=True)
                return
            backward = self.find_dialog.direction_combobox.currentText() == "向上查找"
            match_cursor = find_wrapped(
                self.text_edit.document(),
                find_str,
                self.text_edit.textCursor(),
                case_sensitive,
                whole_words,
                backward,
            )
            if match_cursor.isNull():
                QMessageBox.information(self, '查找', f'未找到 "{find_str}"')
                self.update_result_label(force_recount=True)
                return
            self.text_edit.setTextCursor(match_cursor)
            self.update_result_label(match_cursor)
        except Exception as exc:
            self.show_error_dialog('查找', f'查找失败: {exc}')

    def replace_next_text(self):
        if not hasattr(self, 'find_dialog'):
            return
        try:
            find_str, replace_str, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
            if not find_str:
                return
            backward = self.find_dialog.direction_combobox.currentText() == "向上查找"
            match_cursor = find_wrapped(
                self.text_edit.document(),
                find_str,
                self.text_edit.textCursor(),
                case_sensitive,
                whole_words,
                backward,
            )
            if match_cursor.isNull():
                QMessageBox.information(self, '替换', f'未找到 "{find_str}"')
                self.update_result_label(force_recount=True)
                return
            match_cursor.insertText(replace_str)
            if replace_str:
                match_cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, len(replace_str))
            self.text_edit.setTextCursor(match_cursor)
            self.update_result_label(match_cursor, force_recount=True)
        except Exception as exc:
            self.show_error_dialog('替换', f'替换失败: {exc}')

    def replace_all_text(self):
        if not hasattr(self, 'find_dialog'):
            return
        try:
            find_str, replace_str, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
            if not find_str:
                QMessageBox.information(self, '替换', '请先输入需要查找的文本。')
                return
            replacements = replace_all(
                self.text_edit.document(),
                find_str,
                replace_str,
                case_sensitive,
                whole_words,
            )
            self.update_result_label(force_recount=True)
            if replacements > 0:
                QMessageBox.information(self, '替换', f'全部替换完成，共替换了 {replacements} 个匹配项。')
            else:
                QMessageBox.information(self, '查找', f'未找到 "{find_str}"')
        except Exception as exc:
            self.show_error_dialog('替换', f'全部替换失败: {exc}')

    def update_result_label(self, cursor=None, force_recount=False):
        if not hasattr(self, 'find_dialog'):
            return
        find_str, _, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
        if not find_str:
            self.find_dialog.result_label.setText("0/0")
            self.reset_find_cache()
            return
        key = (find_str, case_sensitive, whole_words)
        if force_recount or self.find_cache.get("key") != key:
            matches = self._collect_matches(find_str, case_sensitive, whole_words)
            self.find_cache = {"key": key, "matches": matches}
        matches = self.find_cache.get("matches", [])
        total_matches = len(matches)
        if total_matches == 0:
            self.find_dialog.result_label.setText("0/0")
            return
        current_cursor = cursor or self.text_edit.textCursor()
        current_index = self._determine_current_match(current_cursor, matches)
        self.find_dialog.result_label.setText(f"{current_index}/{total_matches}")

    def _build_find_flags(self, case_sensitive, whole_words):
        return build_find_flags(case_sensitive, whole_words)

    def _collect_matches(self, find_str, case_sensitive, whole_words):
        return collect_matches(self.text_edit.document(), find_str, case_sensitive, whole_words)

    def _determine_current_match(self, cursor, matches):
        return determine_current_match(cursor, matches)

    def bold_text(self):
        cursor = self.text_edit.textCursor()
        if cursor.charFormat().fontWeight() != QFont.Bold:
            cursor.mergeCharFormat(self.bold_format())
        else:
            cursor.mergeCharFormat(self.normal_format())

    def italic_text(self):
        cursor = self.text_edit.textCursor()
        if not cursor.charFormat().fontItalic():
            cursor.mergeCharFormat(self.italic_format())
        else:
            cursor.mergeCharFormat(self.normal_format())

    def bold_format(self):
        format_ = QTextCharFormat()
        format_.setFontWeight(QFont.Bold)
        return format_

    def italic_format(self):
        format_ = QTextCharFormat()
        format_.setFontItalic(True)
        return format_

    def normal_format(self):
        format_ = QTextCharFormat()
        format_.setFontWeight(QFont.Normal)
        format_.setFontItalic(False)
        return format_

    def open_settings_dialog(self):
        try:
            font, ok = QFontDialog.getFont(self.text_edit.font(), self, "字体设置")
            if ok:
                self.text_edit.setFont(font)
        except Exception as exc:
            self.show_error_dialog('字体设置', f'无法打开字体设置: {exc}')

    def toggle_line_numbers(self):
        try:
            self.text_edit.line_numbers_visible = self.show_line_numbers_action.isChecked()
            self.text_edit.updateLineNumberAreaWidth(0)
            self.text_edit.update()
        except Exception as exc:
            self.show_error_dialog('行号', f'切换行号显示失败: {exc}')

    def toggle_auto_wrap(self, checked):
        self.text_edit.setLineWrapMode(QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap)

    def set_line_number_color(self):
        try:
            color = QColorDialog.getColor()
            if color.isValid():
                self.text_edit.lineNumberColor = color
                self.text_edit.lineNumberArea.update()
        except Exception as exc:
            self.show_error_dialog('行号颜色', f'设置行号颜色失败: {exc}')

    def set_text_color(self):
        try:
            color = QColorDialog.getColor()
            if color.isValid():
                # 获取颜色的 RGB 值
                r, g, b, _ = color.getRgb()

                # 计算颜色的亮度（使用感知亮度公式）
                brightness = (r * 0.299 + g * 0.587 + b * 0.114)

                # 根据亮度设置相应的背景色
                if brightness > 186:  # 如果颜色较亮，则设置背景为黑色
                    background_color = '#000000'  # 黑色
                else:  # 如果颜色较暗，则设置背景为白色
                    background_color = '#FFFFFF'  # 白色

                # 设置文本颜色和背景颜色
                self.text_edit.setStyleSheet(f'color: {color.name()}; background-color: {background_color};')
        except Exception as exc:
            self.show_error_dialog('文本颜色', f'设置文本颜色失败: {exc}')

    def handle_document_modified(self):
        self.status_label_doc.setText("文档状态: 已修改")
        self.update_file_size()
        self.is_saved = False

    def update_insert_overwrite_mode(self):
        try:
            mode = "OVR" if self.text_edit.overwriteMode() else "INS"
            self.status_label_insert_mode.setText(mode)
        except Exception as exc:
            print(f"更新插入/改写状态失败: {exc}")

    def closeEvent(self, event):
        if not self.maybe_save_current_document():
            event.ignore()
            return
        event.accept()

    def on_text_changed(self):
        self.is_saved = False  # 文本更改后，设置未保存标志
        self.reset_find_cache()

    def run_current_python_file(self):
        if not self.file_path or not self.file_path.lower().endswith(('.py', '.pyw')):
            QMessageBox.information(self, '运行 Python', '当前文件不是 Python 文件。')
            return

        if self.text_edit.document().isModified():
            if not self.save_file():
                return

        try:
            result = subprocess.run(
                [sys.executable, self.file_path],
                cwd=os.path.dirname(self.file_path) or None,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, '运行 Python', '运行超时（30 秒）。')
            return
        except Exception as exc:
            self.show_error_dialog('运行 Python', f'运行失败: {exc}')
            return

        output = result.stdout or ''
        if result.stderr:
            output += ('\n' if output else '') + result.stderr
        if not output:
            output = f'进程已退出，返回码: {result.returncode}'
        else:
            output += f'\n\n返回码: {result.returncode}'
        QMessageBox.information(self, '运行结果', output[:8000])

    def update_file_size(self):
        try:
            if self.file_path and os.path.isfile(self.file_path):
                size = os.path.getsize(self.file_path)
                human_readable_size = self.convert_size(size)
                self.status_label_file_size.setText(f"文件大小: {human_readable_size}")
            else:
                self.status_label_file_size.setText("文件大小: N/A")
        except Exception as exc:
            self.status_label_file_size.setText("文件大小: N/A")
            print(f'更新文件大小失败: {exc}')

    def show_error_dialog(self, title, message):
        QMessageBox.critical(self, title, message)

    def _read_file_with_fallback(self, file_path):
        return read_text_file_with_fallback(file_path, chardet_module=chardet)

    def reset_find_cache(self):
        self.find_cache = {"key": None, "matches": []}

    def convert_size(self, size):
        return convert_size(size)


def open_with_yunji(paths=None, plugin_dirs=None, load_plugins=True):
    app = QApplication(sys.argv)
    paths = [os.fspath(path) for path in (paths or [])]
    editors = []

    if paths:
        for index, path in enumerate(paths):
            editor = YunjiEditor(plugin_dirs=plugin_dirs, load_plugins=load_plugins)
            editor.open_path(path)
            editor.show()
            editors.append(editor)
    else:
        editor = YunjiEditor(plugin_dirs=plugin_dirs, load_plugins=load_plugins)
        editor.show()
        editors.append(editor)

    app.exec_()


def build_arg_parser():
    parser = argparse.ArgumentParser(description='Yunji 文本编辑器')
    parser.add_argument('paths', nargs='*', help='要打开的文件或目录')
    parser.add_argument('--version', action='version', version=f'yunji {__version__}')
    parser.add_argument('--no-plugins', action='store_true', help='启动时不加载插件')
    parser.add_argument(
        '--plugin-dir',
        action='append',
        default=None,
        help='额外插件目录，可重复指定。插件文件需提供 activate(editor) 函数。',
    )
    return parser


def cli_editor(argv=None):
    args = build_arg_parser().parse_args(argv)
    open_with_yunji(
        paths=args.paths,
        plugin_dirs=args.plugin_dir,
        load_plugins=not args.no_plugins,
    )


if __name__ == "__main__":
    cli_editor()
