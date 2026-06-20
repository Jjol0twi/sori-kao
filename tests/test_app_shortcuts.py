"""GUI 입력창 편집 단축키 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from app import bind_text_edit_shortcuts


class FakeEntry:
    def __init__(self):
        self.bindings = {}
        self.text = "hello"
        self.cursor = 5
        self.selection = None
        self.clipboard = "!"

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def selection_present(self):
        return self.selection is not None

    def selection_get(self):
        if self.selection is None:
            raise ValueError("no selection")
        start, end = self.selection
        return self.text[start:end]

    def get(self):
        return self.text

    def index(self, which):
        if self.selection is None:
            raise ValueError("no selection")
        start, end = self.selection
        if which == "sel.first":
            return start
        if which == "sel.last":
            return end
        raise ValueError(which)

    def selection_range(self, start, end):
        if end == "end":
            end = len(self.text)
        self.selection = (start, end)

    def icursor(self, index):
        self.cursor = len(self.text) if index == "end" else index

    def clipboard_get(self):
        return self.clipboard

    def clipboard_clear(self):
        self.clipboard = ""

    def clipboard_append(self, text):
        self.clipboard += text

    def delete(self, start, end=None):
        if start == "sel.first" and end == "sel.last":
            start, end = self.selection
            self.selection = None
        self.text = self.text[:start] + self.text[end:]
        self.cursor = start

    def insert(self, index, text):
        if index == "insert":
            index = self.cursor
        self.text = self.text[:index] + text + self.text[index:]
        self.cursor = index + len(text)


class FakeEvent:
    def __init__(self, widget):
        self.widget = widget


def test_input_entry_binds_macos_edit_shortcuts():
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry, is_macos=True)

    for sequence in ("<Command-a>", "<Command-c>", "<Command-v>", "<Command-x>"):
        assert sequence in entry.bindings

    assert entry.bindings["<Command-a>"](FakeEvent(entry)) == "break"
    assert entry.selection == (0, 5)

    assert entry.bindings["<Command-c>"](FakeEvent(entry)) == "break"
    assert entry.clipboard == "hello"

    entry.clipboard = "붙여넣기"
    entry.selection = None
    entry.cursor = len(entry.text)
    assert entry.bindings["<Command-v>"](FakeEvent(entry)) == "break"
    assert entry.text == "hello붙여넣기"

    entry.selection = (5, len(entry.text))
    assert entry.bindings["<Command-x>"](FakeEvent(entry)) == "break"
    assert entry.clipboard == "붙여넣기"
    assert entry.text == "hello"


def test_input_entry_binds_control_edit_shortcuts():
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry, is_macos=False)

    for sequence in ("<Control-a>", "<Control-c>", "<Control-v>", "<Control-x>"):
        assert sequence in entry.bindings

    entry.cursor = len(entry.text)
    assert entry.bindings["<Control-v>"](FakeEvent(entry)) == "break"
    assert entry.text == "hello!"


def test_main_reports_tk_runtime_error(monkeypatch, capsys):
    def fail_tk():
        raise app.tk.TclError("missing init.tcl")

    monkeypatch.setattr(app.tk, "Tk", fail_tk)

    assert app.main() == 1

    captured = capsys.readouterr()
    assert "Tk GUI를 시작할 수 없습니다" in captured.err
    assert "missing init.tcl" in captured.err
