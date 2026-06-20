"""GUI 입력창 편집 단축키 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from app import bind_text_edit_shortcuts


class FakeEntry:
    """편집 단축키가 Tk 표준 가상이벤트로 위임되는지 기록하는 가짜 입력창."""

    def __init__(self):
        self.bindings = {}
        self.generated = []
        self.selection = None
        self.cursor = None

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def event_generate(self, virtual):
        self.generated.append(virtual)

    def selection_range(self, start, end):
        self.selection = (start, end)

    def icursor(self, index):
        self.cursor = index


class FakeEvent:
    def __init__(self, widget):
        self.widget = widget


def test_input_entry_binds_macos_edit_shortcuts():
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry, is_macos=True)

    for sequence in ("<Command-a>", "<Command-c>", "<Command-v>", "<Command-x>"):
        assert sequence in entry.bindings

    # 복사/붙여넣기/잘라내기는 Tk 표준 가상이벤트로 위임한다(플랫폼 네이티브 동작).
    assert entry.bindings["<Command-c>"](FakeEvent(entry)) == "break"
    assert entry.generated[-1] == "<<Copy>>"
    assert entry.bindings["<Command-v>"](FakeEvent(entry)) == "break"
    assert entry.generated[-1] == "<<Paste>>"
    assert entry.bindings["<Command-x>"](FakeEvent(entry)) == "break"
    assert entry.generated[-1] == "<<Cut>>"

    # 전체 선택은 직접 처리한다.
    assert entry.bindings["<Command-a>"](FakeEvent(entry)) == "break"
    assert entry.selection == (0, "end")


def test_input_entry_binds_control_edit_shortcuts():
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry, is_macos=False)

    for sequence in ("<Control-a>", "<Control-c>", "<Control-v>", "<Control-x>"):
        assert sequence in entry.bindings

    # macOS가 아니어도 Control 단축키가 같은 가상이벤트로 위임된다.
    assert entry.bindings["<Control-v>"](FakeEvent(entry)) == "break"
    assert entry.generated == ["<<Paste>>"]


def test_main_reports_tk_runtime_error(monkeypatch, capsys):
    def fail_tk():
        raise app.tk.TclError("missing init.tcl")

    monkeypatch.setattr(app.tk, "Tk", fail_tk)

    assert app.main() == 1

    captured = capsys.readouterr()
    assert "Tk GUI를 시작할 수 없습니다" in captured.err
    assert "missing init.tcl" in captured.err
