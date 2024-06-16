# test_editor.py

import unittest
import os
from PyQt5.QtWidgets import QApplication
from yunji.editor import YunjiEditor

class TestYunjiEditor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication([])

    def setUp(self):
        self.editor = YunjiEditor()

    def tearDown(self):
        self.editor.close()

    def test_initial_state(self):
        self.assertIsNone(self.editor.file_path)
        self.assertEqual(self.editor.status_label_center.text(), "行: 1 ;  列: 1")
        self.assertEqual(self.editor.status_label_right.text(), "文档状态: 未修改")

    def test_set_text(self):
        test_text = "Hello, world!"
        self.editor.text_edit.setPlainText(test_text)
        self.assertEqual(self.editor.text_edit.toPlainText(), test_text)
        self.assertFalse(self.editor.is_saved)
        self.assertEqual(self.editor.status_label_right.text(), "文档状态: 已修改")

    def test_save_file(self):
        test_text = "Hello, world!"
        self.editor.text_edit.setPlainText(test_text)
        test_file = 'testfile.txt'
        self.editor.file_path = test_file
        self.editor.save_file()
        self.assertTrue(self.editor.is_saved)
        with open(test_file, 'r') as file:
            self.assertEqual(file.read(), test_text)
        os.remove(test_file)  # 清理测试文件

    def test_open_file(self):
        test_text = "Hello, world!"
        test_file = 'testfile.txt'
        with open(test_file, 'w') as file:
            file.write(test_text)
        self.editor.open_file(test_file)
        self.assertEqual(self.editor.text_edit.toPlainText(), test_text)
        self.assertEqual(self.editor.file_path, test_file)
        os.remove(test_file)  # 清理测试文件

    def test_line_number_visibility(self):
        self.editor.text_edit.line_numbers_visible = True
        self.editor.text_edit.updateLineNumberAreaWidth(0)
        self.assertTrue(self.editor.text_edit.lineNumberArea.isVisible())

if __name__ == '__main__':
    unittest.main()
