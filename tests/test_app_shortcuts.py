"""GUI 입력창 편집 단축키 테스트(직접 클립보드 조작)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from app import bind_text_edit_shortcuts


class FakeEntry:
    """tk.Entry의 클립보드/선택 동작을 흉내내는 가짜 입력창."""

    def __init__(self):
        self.bindings = {}
        self.text = ""
        self.cursor = 0
        self.selection = None
        self.clipboard = ""

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def selection_present(self):
        return self.selection is not None

    def select_range(self, start, end):
        if end == "end":
            end = len(self.text)
        self.selection = (start, end)

    selection_range = select_range

    def index(self, which):
        start, end = self.selection
        return start if which == "sel.first" else end

    def get(self):
        return self.text

    def icursor(self, index):
        self.cursor = len(self.text) if index == "end" else index

    def clipboard_clear(self):
        self.clipboard = ""

    def clipboard_append(self, text):
        self.clipboard += text

    def clipboard_get(self):
        return self.clipboard

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


class FakeRoot:
    """bind_all 호출을 기록하는 가짜 루트."""

    def __init__(self):
        self.all_bindings = {}

    def bind_all(self, sequence, callback):
        self.all_bindings[sequence] = callback


def test_macos_binds_both_command_and_control_globally():
    root = FakeRoot()
    bind_text_edit_shortcuts(root, lambda: None, is_macos=True)
    for modifier in ("Command", "Control"):
        for key in ("a", "c", "v", "x"):
            assert f"<{modifier}-{key}>" in root.all_bindings


def test_non_macos_binds_control_only():
    root = FakeRoot()
    bind_text_edit_shortcuts(root, lambda: None, is_macos=False)
    assert "<Control-c>" in root.all_bindings
    assert not any(seq.startswith("<Command-") for seq in root.all_bindings)


def test_shortcuts_act_on_focused_widget():
    root = FakeRoot()
    entry = FakeEntry()
    entry.text = "hello"
    bind_text_edit_shortcuts(root, lambda: entry, is_macos=True)

    def fire(sequence):
        return root.all_bindings[sequence]()

    # 전체 선택
    assert fire("<Command-a>") == "break"
    assert entry.selection == (0, 5)

    # 복사 → 클립보드에 선택 텍스트
    assert fire("<Command-c>") == "break"
    assert entry.clipboard == "hello"

    # 붙여넣기 → 선택 영역을 클립보드 내용으로 대체
    entry.clipboard = "X"
    entry.selection = (0, 5)
    entry.cursor = 5
    assert fire("<Command-v>") == "break"
    assert entry.text == "X"

    # 잘라내기 → 클립보드에 담고 선택 영역 삭제
    entry.text = "hello"
    entry.selection = (0, 5)
    entry.clipboard = ""
    assert fire("<Control-x>") == "break"
    assert entry.clipboard == "hello"
    assert entry.text == ""


def test_main_reports_tk_runtime_error(monkeypatch, capsys):
    def fail_tk():
        raise app.tk.TclError("missing init.tcl")

    monkeypatch.setattr(app.tk, "Tk", fail_tk)

    assert app.main() == 1

    captured = capsys.readouterr()
    assert "Tk GUI를 시작할 수 없습니다" in captured.err
    assert "missing init.tcl" in captured.err
