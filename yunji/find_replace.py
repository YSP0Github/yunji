from PyQt5.QtWidgets import (
    QDialog, QLabel, QLineEdit, QCheckBox, QPushButton,
    QComboBox, QVBoxLayout, QHBoxLayout,
)
from PyQt5.QtCore import Qt, QEvent


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
