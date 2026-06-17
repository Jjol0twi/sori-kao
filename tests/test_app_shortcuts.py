"""GUI 입력창 편집 단축키 테스트."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import bind_text_edit_shortcuts


class FakeEntry:
    def __init__(self):
        self.bindings = {}
        self.generated = []

    def bind(self, sequence, callback):
        self.bindings[sequence] = callback

    def event_generate(self, virtual_event):
        self.generated.append(virtual_event)


class FakeEvent:
    def __init__(self, widget):
        self.widget = widget


def test_input_entry_binds_macos_edit_shortcuts():
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry, is_macos=True)

    expected = {
        "<Command-a>": "<<SelectAll>>",
        "<Command-c>": "<<Copy>>",
        "<Command-v>": "<<Paste>>",
        "<Command-x>": "<<Cut>>",
    }
    for sequence, virtual_event in expected.items():
        assert sequence in entry.bindings
        assert entry.bindings[sequence](FakeEvent(entry)) == "break"
        assert entry.generated[-1] == virtual_event


def test_input_entry_binds_control_edit_shortcuts():
    entry = FakeEntry()
    bind_text_edit_shortcuts(entry, is_macos=False)

    expected = {
        "<Control-a>": "<<SelectAll>>",
        "<Control-c>": "<<Copy>>",
        "<Control-v>": "<<Paste>>",
        "<Control-x>": "<<Cut>>",
    }
    for sequence, virtual_event in expected.items():
        assert sequence in entry.bindings
        assert entry.bindings[sequence](FakeEvent(entry)) == "break"
        assert entry.generated[-1] == virtual_event
