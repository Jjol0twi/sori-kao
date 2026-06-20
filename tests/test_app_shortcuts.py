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


def test_input_entry_binds_ctrl_edit_shortcuts_via_virtual_events():
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry)

    for sequence in ("<Control-a>", "<Control-c>", "<Control-v>", "<Control-x>"):
        assert sequence in entry.bindings

    # 복사/붙여넣기/잘라내기는 Tk 표준 가상이벤트로 위임한다(플랫폼 네이티브 동작).
    assert entry.bindings["<Control-c>"](FakeEvent(entry)) == "break"
    assert entry.generated[-1] == "<<Copy>>"
    assert entry.bindings["<Control-v>"](FakeEvent(entry)) == "break"
    assert entry.generated[-1] == "<<Paste>>"
    assert entry.bindings["<Control-x>"](FakeEvent(entry)) == "break"
    assert entry.generated[-1] == "<<Cut>>"

    # 전체 선택은 가상이벤트 의존성을 피해 직접 처리한다.
    assert entry.bindings["<Control-a>"](FakeEvent(entry)) == "break"
    assert entry.selection == (0, "end")


def test_command_shortcuts_are_left_to_the_edit_menu():
    # macOS Cmd 단축키는 입력창 바인딩이 아니라 표준 '편집 메뉴'에서 처리한다.
    # 따라서 bind_text_edit_shortcuts는 Command 바인딩을 걸지 않는다.
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry, is_macos=True)
    assert not any(seq.startswith("<Command-") for seq in entry.bindings)


def test_main_reports_tk_runtime_error(monkeypatch, capsys):
    def fail_tk():
        raise app.tk.TclError("missing init.tcl")

    monkeypatch.setattr(app.tk, "Tk", fail_tk)

    assert app.main() == 1

    captured = capsys.readouterr()
    assert "Tk GUI를 시작할 수 없습니다" in captured.err
    assert "missing init.tcl" in captured.err
