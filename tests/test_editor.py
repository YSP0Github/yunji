import os
import shutil
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication

from yunji.editor import YunjiEditor, build_arg_parser
from yunji.plugin_manager import PluginManager
from yunji.syntax_highlighter import language_for_path


@unittest.skipUnless(
    os.environ.get("YUNJI_RUN_GUI_TESTS") == "1",
    "PyQt GUI tests are opt-in. Set YUNJI_RUN_GUI_TESTS=1 to run them.",
)
class TestYunjiEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.editor = YunjiEditor()

    def tearDown(self):
        self.editor.is_saved = True
        self.editor.text_edit.document().setModified(False)
        self.editor.close()

    def test_initial_state(self):
        self.assertIsNone(self.editor.file_path)
        self.assertEqual(self.editor.status_label_line.text(), "\u884c: 1 ;  \u5217: 1")
        self.assertEqual(self.editor.status_label_doc.text(), "\u6587\u6863\u72b6\u6001: \u672a\u4fee\u6539")

    def test_set_text_marks_document_modified(self):
        self.editor.text_edit.setPlainText("Hello, world!")
        self.assertEqual(self.editor.text_edit.toPlainText(), "Hello, world!")
        self.assertFalse(self.editor.is_saved)
        self.assertEqual(self.editor.status_label_doc.text(), "\u6587\u6863\u72b6\u6001: \u5df2\u4fee\u6539")

    def test_save_file_marks_document_clean(self):
        path = Path("testfile.txt")
        try:
            self.editor.text_edit.setPlainText("Hello, world!")
            self.editor.file_path = str(path)
            self.assertTrue(self.editor.save_file())
            self.assertTrue(self.editor.is_saved)
            self.assertFalse(self.editor.text_edit.document().isModified())
            self.assertEqual(path.read_text(encoding="utf-8"), "Hello, world!")
        finally:
            path.unlink(missing_ok=True)

    def test_open_file_marks_document_clean(self):
        path = Path("testfile.txt")
        try:
            path.write_text("Hello, world!", encoding="utf-8")
            self.editor.open_file(str(path))
            self.assertEqual(self.editor.text_edit.toPlainText(), "Hello, world!")
            self.assertEqual(self.editor.file_path, str(path))
            self.assertTrue(self.editor.is_saved)
            self.assertFalse(self.editor.text_edit.document().isModified())
        finally:
            path.unlink(missing_ok=True)

    def test_line_number_visibility(self):
        self.editor.show_line_numbers_action.setChecked(True)
        self.editor.toggle_line_numbers()
        self.assertTrue(self.editor.text_edit.line_numbers_visible)
        self.assertTrue(self.editor.text_edit.lineNumberArea.isVisible())

    def test_collect_matches(self):
        self.editor.text_edit.setPlainText("abc abc Abc")
        self.assertEqual(len(self.editor._collect_matches("abc", False, False)), 3)
        self.assertEqual(len(self.editor._collect_matches("abc", True, False)), 2)

    def test_convert_size(self):
        self.assertEqual(self.editor.convert_size(1024), "1.00 KB")

    def test_save_as_filter_adds_python_extension(self):
        self.assertEqual(
            self.editor._ensure_extension_for_filter("script", "Python 文件 (*.py *.pyw)"),
            "script.py",
        )
        self.assertEqual(
            self.editor._ensure_extension_for_filter("script.py", "文本文件 (*.txt)"),
            "script.py",
        )

    def test_new_file_resets_document_state(self):
        self.editor.text_edit.setPlainText("old")
        self.editor.file_path = "old.txt"
        self.editor.text_edit.document().setModified(False)
        self.editor.is_saved = True
        self.assertTrue(self.editor.new_file())
        self.assertEqual(self.editor.text_edit.toPlainText(), "")
        self.assertIsNone(self.editor.file_path)
        self.assertTrue(self.editor.is_saved)
        self.assertFalse(self.editor.text_edit.document().isModified())
        self.assertEqual(self.editor.filename_label.text(), "未命名")

    def test_save_python_file_refreshes_highlighter(self):
        path = Path("tmp_highlight_test.py")
        try:
            self.editor.text_edit.setPlainText("print('hello')")
            self.editor.file_path = str(path)
            self.editor.syntax_highlighter = None
            self.assertTrue(self.editor.save_file())
            self.assertIsNotNone(self.editor.syntax_highlighter)
        finally:
            path.unlink(missing_ok=True)

    def test_tab_inserts_spaces(self):
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier, "\t")
        self.editor.text_edit.keyPressEvent(event)
        self.assertEqual(self.editor.text_edit.toPlainText(), "    ")

    def test_auto_indent_after_colon(self):
        self.editor.text_edit.setPlainText("if True:")
        cursor = self.editor.text_edit.textCursor()
        cursor.movePosition(cursor.End)
        self.editor.text_edit.setTextCursor(cursor)
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_Return, Qt.NoModifier, "\n")
        self.editor.text_edit.keyPressEvent(event)
        self.assertEqual(self.editor.text_edit.toPlainText(), "if True:\n    ")

    def test_auto_pair_parentheses(self):
        event = QKeyEvent(QKeyEvent.KeyPress, Qt.Key_ParenLeft, Qt.NoModifier, "(")
        self.editor.text_edit.keyPressEvent(event)
        self.assertEqual(self.editor.text_edit.toPlainText(), "()")

    def test_run_python_action_exists_with_f5_shortcut(self):
        matches = [
            action for action in self.editor.findChildren(QAction)
            if action.text() == "运行当前 Python 文件"
        ]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].shortcut().toString(), "F5")


class TestProjectFiles(unittest.TestCase):
    def test_requirements_is_plain_pip_format(self):
        content = Path("requirements.txt").read_text(encoding="utf-8")
        self.assertNotIn("```", content)
        self.assertIn("PyQt5", content)
        self.assertIn("chardet", content)


class TestNonGuiFeatures(unittest.TestCase):
    def test_python_language_detection(self):
        self.assertEqual(language_for_path("demo.py"), "python")
        self.assertEqual(language_for_path("demo.pyw"), "python")
        self.assertIsNone(language_for_path("demo.txt"))

    def test_cli_parser(self):
        args = build_arg_parser().parse_args(["--no-plugins", "--plugin-dir", "plugins", "a.py"])
        self.assertTrue(args.no_plugins)
        self.assertEqual(args.plugin_dir, ["plugins"])
        self.assertEqual(args.paths, ["a.py"])

    def test_plugin_manager_loads_activate_function(self):
        plugin_dir = Path("tmp_plugins")
        plugin_file = plugin_dir / "sample.py"
        editor = type("DummyEditor", (), {})()
        try:
            plugin_dir.mkdir(exist_ok=True)
            plugin_file.write_text(
                "def activate(editor):\n    editor.plugin_loaded = True\n",
                encoding="utf-8",
            )
            manager = PluginManager(editor, plugin_dirs=[plugin_dir])
            manager.load_all()
            self.assertTrue(editor.plugin_loaded)
            self.assertEqual(manager.summary(), (1, 0))
        finally:
            shutil.rmtree(plugin_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
