# 云记 (Yunji Editor)

云记是一款基于 PyQt5 的轻量文本编辑器，支持常见的纯文本编辑、查找替换、Python 语法高亮、命令行启动和简单插件扩展。

## 功能

- 打开、保存、另存为
- 新建窗口
- 撤销、重做、剪切、复制、粘贴
- 查找、替换、全部替换
- Python 语法高亮（`.py` / `.pyw`）
- 显示行号、设置行号颜色
- 自动换行
- 字体设置、正文颜色设置
- 命令行打开文件或目录，支持 `--version`、`--plugin-dir`、`--no-plugins`
- 简单插件机制：从插件目录加载带有 `activate(editor)` 的 `.py` 文件
- 状态栏显示路径、行列、编码、文件大小、缩放比例和插入/改写模式

## 快捷键

- `Ctrl+O`：打开文件
- `Ctrl+S`：保存文件
- `Ctrl+Shift+S`：另存为
- `Ctrl+N`：新建窗口
- `Ctrl+Z`：撤销
- `Ctrl+Y`：重做
- `Ctrl+X`：剪切
- `Ctrl+C`：复制
- `Ctrl+V`：粘贴
- `Ctrl+F`：查找
- `Ctrl+H`：替换
- `Ctrl+B`：加粗
- `Ctrl+I`：斜体

## 安装和运行

### 从源码运行

```bash
pip install -r requirements.txt
python -m yunji.editor
```

### 以可编辑模式安装

```bash
pip install -e .
yunji
```

### 打开指定文件或目录

```bash
yunji path/to/file.txt
yunji path/to/project
yunji --version
yunji --no-plugins
yunji --plugin-dir ./plugins path/to/file.py
```

## 插件

Yunji 会自动扫描以下插件目录：

- 当前工作目录下的 `plugins/`
- 用户主目录下的 `.yunji/plugins/`

插件是普通 Python 文件，可提供 `activate(editor)` 函数：

```python
def activate(editor):
    editor.statusBar().showMessage("插件已加载", 3000)
```

也可以通过命令行指定额外插件目录：

```bash
yunji --plugin-dir ./plugins
```

## 开发

运行测试：

```bash
python -m pytest
```

GUI 测试默认跳过。如需在支持 Qt GUI 的环境中运行：

```bash
YUNJI_RUN_GUI_TESTS=1 python -m pytest
```

Windows PowerShell：

```powershell
$env:YUNJI_RUN_GUI_TESTS = "1"
python -m pytest
```

## 项目结构

```text
yunji/
  editor.py             # 主窗口和应用入口
  text_editor.py        # 文本编辑控件与行号区域
  find_replace.py       # 查找/替换对话框
  find_service.py       # 查找/替换纯逻辑
  syntax_highlighter.py # Python 语法高亮
  plugin_manager.py     # 插件发现和加载
  file_io.py            # 文件读取和大小格式化
  images/               # 图标资源
```

## 打包

项目使用 `pyproject.toml` 管理打包元数据，可构建 wheel：

```bash
python -m pip wheel . --no-deps -w dist
```

## License

MIT
