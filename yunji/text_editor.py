import re
import webbrowser

from PyQt5.QtWidgets import QApplication, QPlainTextEdit, QTextEdit, QWidget, QAction
from PyQt5.QtGui import QFont, QTextCursor, QTextFormat, QPainter, QColor
from PyQt5.QtCore import Qt, QSize, QRect, QUrl


class TextEditor(QPlainTextEdit):
    PAIRS = {
        '(': ')',
        '[': ']',
        '{': '}',
        '"': '"',
        "'": "'",
    }

    def __init__(self, parent=None):
        super(TextEditor, self).__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.line_numbers_visible = False
        self.lineNumberColor = QColor(Qt.cyan)
        self.cursorPositionChanged.connect(self.update_cursor_position)
        self.updateLineNumberAreaWidth(0)
        self.main_window = parent
        self.document().contentsChanged.connect(self.document_modified)
        self.setAcceptDrops(True)

        font = QFont("Consolas", 14)
        self.setFont(font)
        self.current_font_size = font.pointSize()
        self.initial_font_size = self.current_font_size
        self.new_font_size = self.current_font_size
        self.indent_width = 4
        self.auto_indent_enabled = True
        self.auto_pair_enabled = True

    def lineNumberAreaWidth(self):
        if not self.line_numbers_visible:
            return 0
        digits = len(str(self.blockCount()))
        return 3 + self.fontMetrics().horizontalAdvance('9') * digits

    def updateLineNumberAreaWidth(self, _):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
        self.lineNumberArea.setVisible(self.line_numbers_visible)

    def updateLineNumberArea(self, rect, dy):
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, event):
        super(TextEditor, self).resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        extraSelections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            lineColor = QColor(Qt.gray).lighter(150)
            selection.format.setBackground(lineColor)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extraSelections.append(selection)
        self.setExtraSelections(extraSelections)

    def wheelEvent(self, event):
        self.current_font_size = self.font().pointSize()
        modifiers = QApplication.keyboardModifiers()
        if modifiers & Qt.ControlModifier:
            angle = event.angleDelta().y()
            self.current_font_size += 1 if angle > 0 else -1
            self.new_font_size = min(max(self.current_font_size, 6), 60)
            font = self.font()
            font.setPointSize(self.new_font_size)
            self.setFont(font)
            self.update_status_label_zoom()
            event.accept()
        else:
            super().wheelEvent(event)

    def update_status_label_zoom(self):
        if self.main_window:
            zoom_percentage = int((self.new_font_size / self.initial_font_size) * 100)
            self.main_window.status_label_zoom.setText(f"{zoom_percentage}%")

    def lineNumberAreaPaintEvent(self, event):
        if not self.line_numbers_visible:
            return

        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(Qt.gray))

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        font = QFont("Consolas")
        font.setPointSize(self.font().pointSize())
        painter.setFont(font)
        painter.setPen(self.lineNumberColor)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0,
                    top,
                    self.lineNumberArea.width(),
                    self.fontMetrics().height(),
                    Qt.AlignRight,
                    str(blockNumber + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def update_cursor_position(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        if self.main_window:
            self.main_window.status_label_line.setText(f"行: {line} ;  列: {col}")

    def document_modified(self):
        if self.document().isModified() and self.main_window:
            try:
                self.main_window.handle_document_modified()
            except Exception as exc:
                print(f"更新文档状态时发生错误: {exc}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Insert and self.main_window:
            super(TextEditor, self).keyPressEvent(event)
            try:
                self.main_window.update_insert_overwrite_mode()
            except AttributeError:
                pass
            return

        if event.key() == Qt.Key_Tab:
            self.textCursor().insertText(' ' * self.indent_width)
            return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and self.auto_indent_enabled:
            self._insert_newline_with_indent()
            return

        text = event.text()
        if self.auto_pair_enabled and text in self.PAIRS:
            self._insert_pair(text, self.PAIRS[text])
            return

        if text in self.PAIRS.values() and self._next_character() == text:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.NextCharacter)
            self.setTextCursor(cursor)
            return

        super(TextEditor, self).keyPressEvent(event)

    def _insert_newline_with_indent(self):
        cursor = self.textCursor()
        block_text = cursor.block().text()
        indent = re.match(r"\s*", block_text).group(0)
        before_cursor = block_text[:cursor.positionInBlock()].rstrip()
        if before_cursor.endswith(':'):
            indent += ' ' * self.indent_width
        cursor.insertText('\n' + indent)
        self.setTextCursor(cursor)

    def _insert_pair(self, opening, closing):
        cursor = self.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            cursor.insertText(opening + selected + closing)
        else:
            cursor.insertText(opening + closing)
            cursor.movePosition(QTextCursor.PreviousCharacter)
        self.setTextCursor(cursor)

    def _next_character(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        return cursor.selectedText()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and self.main_window:
            paths = [url.toLocalFile() for url in urls if url.isLocalFile()]
            if paths:
                self.main_window.open_dropped_paths(paths)
                event.acceptProposedAction()
                return
        super().dropEvent(event)

    def contextMenuEvent(self, event):
        try:
            menu = self.createStandardContextMenu()
            menu.addSeparator()
            custom_action = QAction("打开选中链接", self)
            custom_action.triggered.connect(self.custom_action_triggered)
            menu.addAction(custom_action)
            menu.exec_(event.globalPos())
        except Exception as exc:
            print(f"右键菜单创建失败: {exc}")

    def custom_action_triggered(self):
        try:
            selected_text = self.textCursor().selectedText()
            if selected_text:
                urls = re.findall(r"(https?://[^\s]+)", selected_text)
                for url in urls:
                    webbrowser.open(url)
        except Exception as exc:
            print(f"自定义操作执行失败: {exc}")


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.textEditor = editor

    def sizeHint(self):
        return QSize(self.textEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.textEditor.lineNumberAreaPaintEvent(event)
