# editor

import sys
import os
import chardet
import platform
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPlainTextEdit, 
                             QAction, QFileDialog, QMessageBox, QLabel, QColorDialog,
                              QVBoxLayout, QWidget, QFontDialog, QHBoxLayout, QPushButton,
                               QComboBox, QDialog, QLineEdit, QCheckBox, QStatusBar)
from PyQt5.QtGui import QIcon, QFont, QTextCharFormat, QTextDocument, QTextCursor, QPalette, QColor, QTextFormat, QPainter, QPixmap
from PyQt5.QtCore import Qt, QSize,QEvent,QTimer, QRect


class TextEditor(QPlainTextEdit):
    def __init__(self, parent = None):
        super(TextEditor, self).__init__(parent)
        self.lineNumberArea = LineNumberArea(self)
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        self.cursorPositionChanged.connect(self.highlightCurrentLine)
        self.line_numbers_visible = False  # 用于控制行号区域的可见性
        self.lineNumberColor = QColor(Qt.cyan)  # 默认行号颜色
        self.cursorPositionChanged.connect(self.update_cursor_position)
        self.updateLineNumberAreaWidth(0)
        self.parent = parent  # 设置对父对象的引用
         # 连接文档修改信号到槽函数
        self.document().contentsChanged.connect(self.document_modified)
        # 初始化字体大小
        font = QFont("Consolas", 14)
        self.setFont(font)
        self.current_font_size = font.pointSize()
        self.initial_font_size = self.current_font_size

    def lineNumberAreaWidth(self):
        if not self.line_numbers_visible:
            return 0
        digits = len(str(self.blockCount()))
        space = 3 + self.fontMetrics().width('9') * digits
        return space

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
        if modifiers & Qt.ControlModifier :
            angle = event.angleDelta().y()
            if angle > 0:
                self.current_font_size += 1
            else:
                self.current_font_size -= 1
            self.new_font_size = min(max(self.current_font_size,6),60)
            font = self.font()
            font.setPointSize(self.new_font_size)
            self.setFont(font)
            
            # 更新状态栏中的放大倍数
            self.update_status_label_zoom()

            event.accept()
        else:
            super().wheelEvent(event)

    def update_status_label_zoom(self):
        if self.parent:
            zoom_percentage = int((self.new_font_size / self.initial_font_size) * 100)
            self.parent.status_label_zoom.setText(f"{zoom_percentage}%")

    def lineNumberAreaPaintEvent(self, event):
        if not self.line_numbers_visible:
            return
        
        painter = QPainter(self.lineNumberArea)
        
        # 设置行号区域的背景颜色
        backgroundColor = QColor(Qt.gray)  # 例如，浅灰色
        painter.fillRect(event.rect(), backgroundColor)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        self.topnumber = blockNumber
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        # 设置行号的字体
        font = QFont("Consolas")
        font.setPointSize(self.font().pointSize())
        painter.setFont(font)

        # 设置行号的字体颜色
        painter.setPen(self.lineNumberColor)

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.drawText(0, top, self.lineNumberArea.width(), self.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1
        return 
    
    def update_cursor_position(self):
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        if self.parent:
            self.parent.status_label_line.setText(f"行: {line} ;  列: {col}")

    def document_modified(self):
        if self.document().isModified() and self.parent:
            self.parent.status_label_doc.setText("文档状态: 已修改")
            self.parent.update_file_size()
            self.is_saved = False  # 文本更改后，设置未保存标志

    def keyPressEvent(self, event):
        super(TextEditor, self).keyPressEvent(event)
        if event.key() == Qt.Key_Insert:
            self.parent.update_insert_overwrite_mode()

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.textEditor = editor

    def sizeHint(self):
        return QSize(self.textEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.textEditor.lineNumberAreaPaintEvent(event)

class FindReplaceDialog(QDialog):
    def __init__(self, parent=None, find=False, initial_text=''):
        super(FindReplaceDialog, self).__init__(parent)

        self.setWindowTitle("查找" if not find else "查找和替换")

        self.find_label = QLabel("查找内容:")
        self.find_input = QLineEdit()
        self.find_input.setText(initial_text)  # 设置初始文本

        # 添加显示查找结果数量和当前位置的 QLabel
        self.result_label = QLabel("0/0")
        self.result_label.setFixedWidth(50)  # 设置宽度，使其与其他控件对齐

        self.replace_label = QLabel("替换为:")
        self.replace_input = QLineEdit()

        self.case_checkbox = QCheckBox("区分大小写")
        self.whole_checkbox = QCheckBox("全字匹配")

        self.find_button = QPushButton("查找")
        self.replace_button = QPushButton("替换")
        self.replace_all_button = QPushButton("全部替换")

        # 添加方向选择下拉框
        self.direction_combobox = QComboBox()
        self.direction_combobox.addItems(["向下查找", "向上查找"])

        layout = QVBoxLayout()
        find_layout = QHBoxLayout()
        button_layout = QHBoxLayout()

        # 将查找输入框、结果显示标签和方向选择框放在同一行
        find_layout.addWidget(self.find_input)
        find_layout.addWidget(self.result_label)
        find_layout.addWidget(self.direction_combobox)

        layout.addWidget(self.find_label)
        layout.addLayout(find_layout)
        layout.addWidget(self.case_checkbox)
        layout.addWidget(self.whole_checkbox)

        button_layout.addWidget(self.find_button)

        if find:
            layout.addWidget(self.replace_label)
            layout.addWidget(self.replace_input)
            button_layout.addWidget(self.replace_button)
            button_layout.addWidget(self.replace_all_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.installEventFilter(self)  # 安装事件过滤器

        # # 连接查找按钮和替换按钮的点击事件到相应功能
        # self.find_button.clicked.connect(self.perform_find)
        # self.replace_button.clicked.connect(self.perform_replace)
        # self.replace_all_button.clicked.connect(self.perform_replace_all)


    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_H and event.modifiers() == Qt.ControlModifier:
                self.parent().replace_text()  # 调用父窗口的替换对话框方法
                self.close()  # 关闭当前查找对话框
                return True
            elif event.key() == Qt.Key_F and event.modifiers() == Qt.ControlModifier:
                self.parent().find_text()  # 调用父窗口的查找对话框方法
                self.close()  # 关闭当前替换对话框
                return True
        return super(FindReplaceDialog, self).eventFilter(source, event)

    def get_find_replace_texts(self):
        return (
            self.find_input.text(),
            self.replace_input.text(),
            self.case_checkbox.isChecked(),
            self.whole_checkbox.isChecked()
        )


class YunjiEditor(QMainWindow):
    def __init__(self, filename=None):
        super().__init__()
        self.init_ui()
        self.file_path = None  # 初始化文件路径为None，表示未保存过
        self.temp_file = None
        self.child_windows = []  # 存储子窗口实例的列表
        self.is_saved = True  # 用于跟踪文件是否已保存
        self.text_edit.textChanged.connect(self.on_text_changed)
        if filename:
            self.open_file(filename)

    def init_ui(self): 
        # 创建一个主窗口的中央小部件，并设置为布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

         # 设置布局小部件的背景颜色
        background_widget = QWidget()
        background_widget.setStyleSheet("QWidget { background-color: #99CCCC; }")
        background_widget.setFixedHeight(1)
        layout.addWidget(background_widget)

        # 文件名标签
        self.filename_label = QLabel("  ")
        self.filename_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.filename_label.setFixedHeight(20)
        self.filename_label.setContentsMargins(5, 0, 0, 0)
        self.filename_label.setStyleSheet("QLabel { background-color: #A4DDD3; color: #996600; }")
        self.filename_label.setFont(QFont("Consolas", 12))
        layout.addWidget(self.filename_label, alignment=Qt.AlignLeft)

        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 创建状态栏的标签
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

         # 添加百分比（放大倍数）标签
        self.status_label_zoom = QLabel("100%")
        self.status_label_zoom.setContentsMargins(10, 0, 10, 0)

        # 添加文件编码标签
        self.status_label_encoding = QLabel("UTF-8")
        self.status_label_encoding.setContentsMargins(10, 0, 10, 0)

        # 添加文件大小标签
        self.status_label_file_size = QLabel("文件大小: 0 B")
        self.status_label_file_size.setContentsMargins(10, 0, 10, 0)

        # 根据操作系统信息设置换行符类型
        os_info = platform.system()
        if os_info == "Windows":
            line_ending_info = "(CRLF)"
        elif os_info in ["Linux", "Darwin"]:  # Darwin 是 macOS 的系统标识
            line_ending_info = "(LF)"
        else:
            line_ending_info = "未知"

        # 添加操作系统信息标签
        self.status_label_os_info = QLabel(f"{os_info} {line_ending_info}")
        self.status_label_os_info.setContentsMargins(10, 0, 10, 0)

        # 将标签添加到状态栏
        self.status_bar.addWidget(self.status_label_filepath, 3)
        self.status_bar.addWidget(self.status_label_line, 1)
        self.status_bar.addWidget(self.status_label_zoom, 1)
        self.status_bar.addWidget(self.status_label_encoding, 1)
        self.status_bar.addWidget(self.status_label_file_size, 1)
        self.status_bar.addPermanentWidget(self.status_label_os_info, 1)
        self.status_bar.addPermanentWidget(self.status_label_doc, 1)

        #创建文本框-------------------------------------
        self.text_edit = TextEditor(parent=self)
        # self.text_edit.setPlainText("Hello\n" * 500)  # 添加大量文本用于测试

        # 设置 QTextEdit 的光标颜色和粗细
        palette = self.text_edit.palette()
        palette.setColor(QPalette.Highlight, QColor("#A4DDD3"))  # 光标颜色
        self.text_edit.setPalette(palette)
        self.text_edit.setStyleSheet("QTextEdit { selection-background-color: #A4DDD3; }")  # 设置选中背景颜色

        layout.addWidget(self.text_edit)
        layout.setContentsMargins(5, 0, 5, 0)

        # 设置图标路径
        icon_base_path = os.path.join(os.path.dirname(__file__), "images")
        open_path = os.path.join(icon_base_path, 'open.png')
        save_path = os.path.join(icon_base_path, 'save.png')
        save_as_path = os.path.join(icon_base_path, 'save_as.png')
        editor_path = os.path.join(icon_base_path, 'editor.png')
        add_path = os.path.join(icon_base_path, 'add.png')
        self.setting_path = os.path.join(icon_base_path, 'setting.png')

        # 创建一个透明图标，用于与复选框对齐
        transparent_pixmap = QPixmap(16, 16)
        transparent_pixmap.fill(Qt.transparent)
        transparent_icon = QIcon(transparent_pixmap)
#region
        # 文件菜单动作
        open_action = QAction(QIcon(open_path), '打开', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_file_dialog)

        save_action = QAction(QIcon(save_path), '保存', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_file)

        save_as_action = QAction(QIcon(save_as_path), '另存为', self)
        save_as_action.setShortcut('Ctrl+Shift+S')
        save_as_action.triggered.connect(self.save_file_as)

        add_action = QAction(QIcon(add_path), '新建窗口', self)  # 新建窗口选项
        add_action.setShortcut('Ctrl+N')
        add_action.triggered.connect(self.new_window)

        # 编辑菜单动作
        undo_action = QAction('撤销', self)
        undo_action.setShortcut('Ctrl+Z')
        undo_action.triggered.connect(self.text_edit.undo)

        redo_action = QAction('重做', self)
        redo_action.setShortcut('Ctrl+Y')
        redo_action.triggered.connect(self.text_edit.redo)

        cut_action = QAction('剪切', self)
        cut_action.setShortcut('Ctrl+X')
        cut_action.triggered.connect(self.text_edit.cut)

        copy_action = QAction('复制', self)
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.text_edit.copy)

        paste_action = QAction('粘贴', self)
        paste_action.setShortcut('Ctrl+V')
        paste_action.triggered.connect(self.text_edit.paste)

        find_action = QAction('查找', self)
        find_action.setShortcut('Ctrl+F')
        find_action.triggered.connect(self.find_text)

        replace_action = QAction('替换', self)
        replace_action.setShortcut('Ctrl+H')
        replace_action.triggered.connect(self.replace_text)

        # 格式菜单动作
        font_bold_action = QAction('加粗', self)
        font_bold_action.setShortcut('Ctrl+B')
        font_bold_action.triggered.connect(self.bold_text)

        font_italic_action = QAction('斜体', self)
        font_italic_action.setShortcut('Ctrl+I')
        font_italic_action.triggered.connect(self.italic_text)

        # 创建设置正文颜色的动作
        text_color_action = QAction('正文颜色', self)
        text_color_action.setIcon(transparent_icon)
        text_color_action.triggered.connect(self.set_text_color)

        # 创建设置行号颜色的动作
        line_number_color_action = QAction('行号颜色', self)
        line_number_color_action.setIcon(transparent_icon)
        line_number_color_action.triggered.connect(self.set_line_number_color)

        # 创建显示行号的动作
        self.show_line_numbers_action = QAction('显示行号', self, checkable=True, checked=False)
        self.show_line_numbers_action.triggered.connect(self.toggle_line_numbers)

        # 创建自动换行的动作和复选框
        auto_wrap_action = QAction('自动换行', self, checkable=True)
        auto_wrap_action.setChecked(True)  # 默认选中自动换行
        auto_wrap_action.triggered.connect(self.toggle_auto_wrap)

        # 创建菜单栏--------------------------------------------------------------------
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu('文件')
        file_menu.addAction(add_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        file_menu.addAction(save_as_action)

        # 编辑菜单
        edit_menu = menubar.addMenu('编辑')
        edit_menu.addAction(undo_action)
        edit_menu.addAction(redo_action)
        edit_menu.addAction(cut_action)
        edit_menu.addAction(copy_action)
        edit_menu.addAction(paste_action)
        edit_menu.addAction(find_action)
        edit_menu.addAction(replace_action)

        # 格式菜单
        format_menu = menubar.addMenu('格式')
        format_menu.addAction(font_bold_action)
        format_menu.addAction(font_italic_action)

        #视图菜单
        view_menu = menubar.addMenu('视图')
        view_menu.addAction(text_color_action)
        view_menu.addAction(line_number_color_action)
        view_menu.addAction(self.show_line_numbers_action)
        view_menu.addAction(auto_wrap_action)
#endregion
        # 创建一个按钮放置在菜单栏右侧
        widget = QWidget(self)
        hbox = QHBoxLayout(widget)
        hbox.setContentsMargins(0, 10, 15, 0)  # 设置右侧留白

        setting_button = QPushButton(QIcon(self.setting_path), '')
        setting_button.setIconSize(QSize(20, 20))  # 设置图标大小为20x20
        setting_button.setToolTip('设置')
        setting_button.clicked.connect(self.open_settings_dialog)
        setting_button.setStyleSheet("QPushButton { width: 18px; height: 18px; background-color: #A4DDD3; border: none }")
        setting_button.setCursor(Qt.PointingHandCursor)  # 添加手形光标

        hbox.addWidget(setting_button, alignment=Qt.AlignRight)
        widget.setLayout(hbox)
        menubar.setCornerWidget(widget, Qt.TopRightCorner)

        self.setGeometry(200, 100, 1000, 900)
        self.setWindowTitle('云记')
        self.setWindowIcon(QIcon(editor_path))
        self.setStyleSheet("""
            QMainWindow {
                background-color: #A4DDD3;
            }
            QTextEdit {
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
        self.show()

    def wheelEvent(self, event):
        self.text_edit.wheelEvent(event)
   
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, '打开文件', '', '所有文件 (*);;文本文件 (*.txt)')
        if file_path:
            self.open_file(file_path)
    
    def open_file(self, file_path):
        self.file_path = file_path

        # 首先尝试使用 UTF-8 编码打开文件
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                self.encoding = 'utf-8'
        except UnicodeDecodeError:
            # 如果 UTF-8 解码失败，使用 chardet 进行编码检测
            with open(self.file_path, 'rb') as file:
                raw_data = file.read()  # 读取整个文件内容以进行准确的编码检测
                result = chardet.detect(raw_data)
                self.encoding = result['encoding']
            
            # 再次尝试用检测到的编码打开文件
            with open(file_path, 'r', encoding=self.encoding) as file:
                content = file.read()

        try:
            self.text_edit.setPlainText(content)
            self.filename_label.setText(os.path.basename(file_path))
            self.status_label_filepath.setText(f'打开文件: {file_path}')
            self.status_label_doc.setText("文档状态: 已打开")
            self.status_label_encoding.setText(self.encoding)
        except FileNotFoundError:
            QMessageBox.critical(self, "File Error", f"文件 '{os.path.basename(file_path)}' 不存在.")
            self.clear_text_edit()  # 清空文本编辑器内容或者执行其他回滚操作
        except Exception as e:
            QMessageBox.critical(self, "Error", f"无法打开文件 '{os.path.basename(file_path)}': {str(e)}")
            self.clear_text_edit()  # 清空文本编辑器内容或者执行其他回滚操作

    def clear_text_edit(self):
        self.text_edit.clear()
        self.status_label_filepath.setText("当前路径: ")
        self.status_label_line.setText("行: 1 ;  列: 1")
        self.status_label_doc.setText("文档状态: 未修改")

    def save_file(self):
        if self.file_path:
            with open(self.file_path, 'w', encoding=self.encoding) as file:
                file.write(self.text_edit.toPlainText())
            self.filename_label.setText(os.path.basename(self.file_path))
            self.status_label_filepath.setText(f'保存文件: {self.file_path}')
            self.status_label_doc.setText("文档状态: 已保存")
            self.is_saved = True  # 设置已保存标志
        else:
            self.save_file_as()

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(self, '另存为', '', '文本文件 (*.txt);;所有文件 (*)')
        if file_path:
            self.file_path = file_path
            with open(file_path, 'w', encoding=self.encoding) as file:
                file.write(self.text_edit.toPlainText())
            self.filename_label.setText(os.path.basename(file_path))
            self.status_label_filepath.setText(f'另存文件: {file_path}')
            self.status_label_doc.setText("文档状态: 已保存")
            self.is_saved = True  # 设置已保存标志

    def new_window(self):
        new_window = YunjiEditor()
        self.child_windows.append(new_window)
        new_window.show()

    def find_text(self):
        if hasattr(self, 'find_dialog') and self.find_dialog.isVisible():
            self.find_dialog.close()
        selected_text = self.text_edit.textCursor().selectedText()
        self.find_dialog = FindReplaceDialog(self, initial_text=selected_text)  # 创建查找/替换对话框实例，传入选中的文本
        
        self.find_dialog.find_button.clicked.connect(self.find_next_text)
        self.find_dialog.show()  # 显示非模态对话框

        # 更新结果标签
        self.update_result_label()

    def replace_text(self):
        if hasattr(self, 'find_dialog') and self.find_dialog.isVisible():
            self.find_dialog.close()
        selected_text = self.text_edit.textCursor().selectedText()
        self.find_dialog = FindReplaceDialog(self, True, initial_text=selected_text)  # 创建查找/替换对话框实例，传入选中的文本
        
        self.find_dialog.find_button.clicked.connect(self.find_next_text)
        self.find_dialog.replace_button.clicked.connect(self.replace_next_text)
        self.find_dialog.replace_all_button.clicked.connect(self.replace_all_text)
        self.find_dialog.show()  # 显示非模态对话框

        # 更新结果标签
        self.update_result_label()

    def find_next_text(self):
        find_str, _, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
        if find_str:
            flags = QTextDocument.FindFlags()
            if case_sensitive:
                flags |= QTextDocument.FindCaseSensitively
            if whole_words:
                flags |= QTextDocument.FindWholeWords

            # 获取查找方向
            if self.find_dialog.direction_combobox.currentText() == "向上查找":
                flags |= QTextDocument.FindBackward

            cursor = self.text_edit.textCursor()
            document = self.text_edit.document()
            cursor = document.find(find_str, cursor, flags)
            if cursor.isNull():
                # 如果查找不到，从文档的另一端重新查找一次
                if flags & QTextDocument.FindBackward:
                    cursor.movePosition(QTextCursor.End)
                else:
                    cursor.movePosition(QTextCursor.Start)

                cursor = document.find(find_str, cursor, flags)
                if cursor.isNull():
                    QMessageBox.information(self, '查找', f'这已经是第一个 "{find_str}"')
                    self.update_result_label(0, 0)
                else:
                    self.text_edit.setTextCursor(cursor)  # 文中高亮显示
                    self.update_result_label(cursor)
            else:
                self.text_edit.setTextCursor(cursor)
                self.update_result_label(cursor)

    def replace_next_text(self):
        find_str, replace_str, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
        if find_str:
            flags = QTextDocument.FindFlags()
            if case_sensitive:
                flags |= QTextDocument.FindCaseSensitively
            if whole_words:
                flags |= QTextDocument.FindWholeWords

            # 获取查找方向
            if self.find_dialog.direction_combobox.currentText() == "向上查找":
                flags |= QTextDocument.FindBackward

            cursor = self.text_edit.textCursor()
            document = self.text_edit.document()
            cursor = document.find(find_str, cursor, flags)
            if cursor.isNull():
                # 如果查找不到，从文档的另一端重新查找一次
                if flags & QTextDocument.FindBackward:
                    cursor.movePosition(QTextCursor.End)
                else:
                    cursor.movePosition(QTextCursor.Start)

                cursor = document.find(find_str, cursor, flags)
                if cursor.isNull():
                    QMessageBox.information(self, '查找', f'这已经是第一个 "{find_str}"')
                    self.update_result_label(0, 0)
                else:
                    cursor.insertText(replace_str)
                    cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, len(replace_str))
                    self.text_edit.setTextCursor(cursor)
                    self.update_result_label(cursor)
            else:
                cursor.insertText(replace_str)
                cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor, len(replace_str))
                self.text_edit.setTextCursor(cursor)
                self.update_result_label(cursor)

    def replace_all_text(self):
        find_str, replace_str, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
        if find_str:
            flags = QTextDocument.FindFlags()
            if case_sensitive:
                flags |= QTextDocument.FindCaseSensitively
            if whole_words:
                flags |= QTextDocument.FindWholeWords

            cursor = self.text_edit.textCursor()
            document = self.text_edit.document()
            replacements = 0
            while True:
                cursor = document.find(find_str, cursor, flags)
                if cursor.isNull():
                    break
                cursor.insertText(replace_str)
                replacements += 1

            self.update_result_label(replacements, replacements)

            if replacements > 0:
                QMessageBox.information(self, '替换', f'全部替换完成，共替换了 {replacements} 个匹配项。')
            else:
                QMessageBox.information(self, '查找', f'未找到 "{find_str}"')

    def update_result_label(self, current_match=0, total_matches=0):
        """更新结果显示标签"""
        if current_match == 0 or total_matches == 0:
            # 重新计算匹配项的总数和当前索引
            find_str, _, case_sensitive, whole_words = self.find_dialog.get_find_replace_texts()
            if find_str:
                flags = QTextDocument.FindFlags()
                if case_sensitive:
                    flags |= QTextDocument.FindCaseSensitively
                if whole_words:
                    flags |= QTextDocument.FindWholeWords

                document = self.text_edit.document()
                total_matches = 0
                current_match = 0

                cursor = QTextCursor(document)
                while not cursor.isNull():
                    cursor = document.find(find_str, cursor, flags)
                    if cursor.isNull():
                        break
                    total_matches += 1
                    if cursor == self.text_edit.textCursor():
                        current_match = total_matches

        self.find_dialog.result_label.setText(f"{current_match}/{total_matches}")

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
        font, ok = QFontDialog.getFont(self.text_edit.font(), self, "字体设置")
        if ok:
            self.text_edit.setFont(font)
    
    def toggle_line_numbers(self):
        self.text_edit.line_numbers_visible = self.show_line_numbers_action.isChecked()
        self.text_edit.updateLineNumberAreaWidth(0)
        self.text_edit.update()
    
    def toggle_auto_wrap(self, checked):
        self.text_edit.setLineWrapMode(QPlainTextEdit.WidgetWidth if checked else QPlainTextEdit.NoWrap)

    def set_line_number_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.text_edit.lineNumberColor = color
            self.text_edit.lineNumberArea.update()
    
    def set_text_color(self):
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

    def closeEvent(self, event):
        if not self.is_saved  and self.text_edit.document().isModified():  # 检查文本内容是否被修改过
            reply = QMessageBox.question(self, '确认关闭', '是否保存已修改的内容?',
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                self.save_file()
            elif reply == QMessageBox.Cancel:
                event.ignore()  # 忽略关闭事件
                return
        event.accept()

    def on_text_changed(self):
        self.is_saved = False  # 文本更改后，设置未保存标志
    
    def update_file_size(self):
        if self.file_path and os.path.isfile(self.file_path):
            size = os.path.getsize(self.file_path)
            human_readable_size = self.convert_size(size)
            self.status_label_file_size.setText(f"文件大小: {human_readable_size}")
        else:
            self.status_label_file_size.setText("文件大小: N/A")

    def convert_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"

def open_with_yunji(filename=None):
    app = QApplication(sys.argv)
    editor = YunjiEditor(filename)
    editor.show()
    app.exec_()

def cli_editor():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        open_with_yunji(file_path)
    else:
        open_with_yunji()

if __name__ == "__main__":
    cli_editor()
