from PyQt5.QtGui import QTextDocument, QTextCursor


def build_find_flags(case_sensitive=False, whole_words=False, backward=False):
    flags = QTextDocument.FindFlags()
    if case_sensitive:
        flags |= QTextDocument.FindCaseSensitively
    if whole_words:
        flags |= QTextDocument.FindWholeWords
    if backward:
        flags |= QTextDocument.FindBackward
    return flags


def find_wrapped(document, find_str, start_cursor, case_sensitive=False, whole_words=False, backward=False):
    flags = build_find_flags(case_sensitive, whole_words, backward)
    match_cursor = document.find(find_str, start_cursor, flags)
    if not match_cursor.isNull():
        return match_cursor

    wrap_cursor = QTextCursor(document)
    wrap_cursor.movePosition(QTextCursor.End if backward else QTextCursor.Start)
    return document.find(find_str, wrap_cursor, flags)


def replace_all(document, find_str, replace_str, case_sensitive=False, whole_words=False):
    flags = build_find_flags(case_sensitive, whole_words)
    edit_cursor = QTextCursor(document)
    edit_cursor.beginEditBlock()
    try:
        search_cursor = QTextCursor(document)
        search_cursor.movePosition(QTextCursor.Start)
        replacements = 0
        while True:
            match_cursor = document.find(find_str, search_cursor, flags)
            if match_cursor.isNull():
                break
            match_cursor.insertText(replace_str)
            replacements += 1
            search_cursor = match_cursor
        return replacements
    finally:
        edit_cursor.endEditBlock()


def collect_matches(document, find_str, case_sensitive=False, whole_words=False):
    cursor = QTextCursor(document)
    cursor.movePosition(QTextCursor.Start)
    flags = build_find_flags(case_sensitive, whole_words)
    matches = []
    while True:
        cursor = document.find(find_str, cursor, flags)
        if cursor.isNull():
            break
        matches.append((cursor.selectionStart(), cursor.selectionEnd()))
    return matches


def determine_current_match(cursor, matches):
    start = cursor.selectionStart()
    end = cursor.selectionEnd()
    for index, (match_start, match_end) in enumerate(matches, start=1):
        if match_start == start and match_end == end:
            return index
    return 0
