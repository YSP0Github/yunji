import os
import sys

# 获取当前文件所在目录
current_directory = os.path.dirname(os.path.abspath(__file__))

# 查找 pythonw.exe 的路径
pythonw_path = os.path.join(sys.exec_prefix, 'pythonw.exe')

# 生成注册表内容
reg_content = f"""Windows Registry Editor Version 5.00

[HKEY_CLASSES_ROOT\\*\\shell\\Open with Yunji]
@="用 云记 打开"
"Icon"="{current_directory}\\yunji\\editor.ico ,0"

[HKEY_CLASSES_ROOT\\*\\shell\\Open with Yunji\\command]
@="\\"{pythonw_path}\\" -m yunji.editor \\"%1\\""
"""

# 将内容写入 reg 文件
reg_file_path = os.path.join(current_directory, 'open_with_yunji.reg')
with open(reg_file_path, 'w') as reg_file:
    reg_file.write(reg_content)

print(f"注册表文件已生成: {reg_file_path}")
