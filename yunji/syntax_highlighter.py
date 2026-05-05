import re

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


PYTHON_EXTENSIONS = {".py", ".pyw"}


def _format(color, bold=False, italic=False):
    text_format = QTextCharFormat()
    text_format.setForeground(QColor(color))
    if bold:
        text_format.setFontWeight(QFont.Bold)
    if italic:
        text_format.setFontItalic(True)
    return text_format


class PythonHighlighter(QSyntaxHighlighter):
    """Small Python syntax highlighter for QPlainTextEdit documents."""

    KEYWORDS = {
        "False", "None", "True", "and", "as", "assert", "async", "await", "break",
        "class", "continue", "def", "del", "elif", "else", "except", "finally", "for",
        "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or",
        "pass", "raise", "return", "try", "while", "with", "yield",
    }

    BUILTINS = {
        "abs", "all", "any", "bool", "dict", "dir", "enumerate", "float", "int", "len",
        "list", "map", "max", "min", "open", "print", "range", "set", "str", "sum", "tuple",
        "type", "zip", "Exception", "ValueError", "RuntimeError",
    }

    def __init__(self, document):
        super().__init__(document)
        self.rules = []
        self.string_format = _format("#a31515")
        self.comment_format = _format("#008000", italic=True)
        self.triple_single = QRegularExpression("'''")
        self.triple_double = QRegularExpression('"""')

        keyword_format = _format("#0000ff", bold=True)
        builtin_format = _format("#795e26")
        number_format = _format("#098658")
        decorator_format = _format("#af00db")
        function_format = _format("#795e26", bold=True)
        class_format = _format("#267f99", bold=True)

        for word in sorted(self.KEYWORDS):
            self.rules.append((QRegularExpression(rf"\b{word}\b"), keyword_format))
        for word in sorted(self.BUILTINS):
            self.rules.append((QRegularExpression(rf"\b{word}\b"), builtin_format))

        self.rules.extend([
            (QRegularExpression(r"\b[0-9]+(\.[0-9]+)?\b"), number_format),
            (QRegularExpression(r"@[A-Za-z_][A-Za-z0-9_]*"), decorator_format),
            (QRegularExpression(r"\bdef\s+([A-Za-z_][A-Za-z0-9_]*)"), function_format, 1),
            (QRegularExpression(r"\bclass\s+([A-Za-z_][A-Za-z0-9_]*)"), class_format, 1),
            (QRegularExpression(r"'(?:\\.|[^'\\])*'"), self.string_format),
            (QRegularExpression(r'"(?:\\.|[^"\\])*"'), self.string_format),
            (QRegularExpression(r"#.*"), self.comment_format),
        ])

    def highlightBlock(self, text):
        for rule in self.rules:
            pattern, fmt = rule[0], rule[1]
            group = rule[2] if len(rule) > 2 else 0
            match = pattern.globalMatch(text)
            while match.hasNext():
                captured = match.next()
                start = captured.capturedStart(group)
                length = captured.capturedLength(group)
                if start >= 0 and length > 0:
                    self.setFormat(start, length, fmt)

        self.setCurrentBlockState(0)
        self._highlight_multiline(text, self.triple_single, 1, self.string_format)
        self._highlight_multiline(text, self.triple_double, 2, self.string_format)

    def _highlight_multiline(self, text, delimiter, state, fmt):
        if self.previousBlockState() == state:
            start = 0
        else:
            match = delimiter.match(text)
            start = match.capturedStart() if match.hasMatch() else -1

        while start >= 0:
            end_match = delimiter.match(text, start + 3)
            if end_match.hasMatch():
                end = end_match.capturedEnd()
                length = end - start
            else:
                self.setCurrentBlockState(state)
                length = len(text) - start
            self.setFormat(start, length, fmt)
            if not end_match.hasMatch():
                break
            next_match = delimiter.match(text, start + length)
            start = next_match.capturedStart() if next_match.hasMatch() else -1


def language_for_path(path):
    if not path:
        return None
    suffix = re.sub(r"^.*(\.[^.]+)$", r"\1", str(path)).lower()
    if suffix in PYTHON_EXTENSIONS:
        return "python"
    return None


def create_highlighter(document, language):
    if language == "python":
        return PythonHighlighter(document)
    return None
