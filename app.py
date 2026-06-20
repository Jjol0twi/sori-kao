"""tkinter GUI와 전체 음운 인상 해석 흐름.

초기에는 입력창 + 해석(Enter) + 초기화 버튼만 있는 작은 창이 뜬다.
입력이 확정되면 창이 아래로 확장되며 1위 음운 인상과 해석 이유·보조 후보를
보여준다. 카모지는 핵심 결과가 아니라 인상 축 아래의 선택적 표시물이다.

색·폰트는 theme.py의 디자인 시스템 토큰을 따르며, 시스템 라이트/다크
모드에 자동으로 반응한다(설정 없이 실시간 재적용).

GUI에는 모델 규칙을 넣지 않고, 보고서 흐름처럼 분석 → 표시 → 설명 순서만
사용자가 눈으로 확인하게 한다.
"""

import sys
import tkinter as tk
from dataclasses import dataclass

from explanation import Explanation, build_explanation
from recommender import KaomojiRecommender, Recommendation, SIZES
from scoring_model import ScoringModel, ScoreResult
from theme import Theme, detect_mode

_EMPTY = "empty"  # 빈 입력 상태 표식
_EDIT_SHORTCUTS = ("a", "c", "v", "x")


@dataclass
class Analysis:
    score: ScoreResult
    recommendation: Recommendation
    explanation: Explanation


def analyze(text: str, model: ScoringModel, recommender: KaomojiRecommender):
    """보고서의 처리 순서와 같은 모양으로 점수·표시·설명을 묶는다."""
    if not text.strip():
        return None
    score = model.score(text)
    return Analysis(score, recommender.recommend(score), build_explanation(score))


# 클립보드 동작은 Tk가 플랫폼별로 구현해 둔 표준 가상이벤트에 위임한다.
# 직접 selection_get/clipboard로 다루면 macOS Aqua에서 복사·붙여넣기가 깨진다.
_EDIT_VIRTUAL = {"c": "<<Copy>>", "v": "<<Paste>>", "x": "<<Cut>>"}


def _make_text_edit_handler(action: str):
    def handler(event):
        entry = event.widget
        if action == "a":
            # 전체 선택은 가상이벤트 의존성(플랫폼차)이 있어 직접 처리한다.
            entry.selection_range(0, "end")
            entry.icursor("end")
        else:
            entry.event_generate(_EDIT_VIRTUAL[action])
        return "break"

    return handler


def bind_text_edit_shortcuts(entry, is_macos: bool = None):
    """Ctrl 기반 편집 단축키를 입력창에 건다(복사/잘라내기/붙여넣기/전체선택).

    macOS의 Cmd 단축키는 위젯 바인딩이 아니라 App '편집 메뉴'에서 처리한다
    (Aqua가 표준 클립보드 단축키를 메뉴로 라우팅하기 때문). is_macos는 호출
    호환을 위해 받지만 Ctrl 바인딩 자체는 플랫폼과 무관하게 동일하다.
    """
    for key in _EDIT_SHORTCUTS:
        handler = _make_text_edit_handler(key)
        entry.bind(f"<Control-{key}>", handler)
        entry.bind(f"<Control-{key.upper()}>", handler)


class KaomojiApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.model = ScoringModel()
        self.recommender = KaomojiRecommender()
        self.theme = Theme(detect_mode())
        self._last = None  # None | _EMPTY | Analysis

        root.title("sori-kao — 음운 인상 해석")
        root.geometry("480x150")  # 시작은 작은 창(이후 내용에 맞춰 재조정)

        self._build()
        self._build_menu()  # macOS Cmd 복사/붙여넣기가 동작하려면 표준 편집 메뉴가 필요
        self._apply_theme()
        self.root.after(120, self._refit)
        self._watch_theme()  # 시스템 테마 변경 실시간 추적

    # ---- 구성 ----
    def _build(self):
        self.container = tk.Frame(self.root)
        self.container.pack(fill="both", expand=True)

        self.input_frame = tk.Frame(self.container, padx=16, pady=14)
        self.input_frame.pack(fill="x")

        self.hint = tk.Label(
            self.input_frame, text="한국어 짧은 표현을 입력하세요",
            font=self.theme.font("hint"), anchor="w",
        )
        self.hint.pack(anchor="w")

        self.entry_row = tk.Frame(self.input_frame)
        self.entry_row.pack(fill="x", pady=(6, 0))
        self.entry = tk.Entry(
            self.entry_row, font=self.theme.font("entry"), width=24,
            relief="solid", borderwidth=1, highlightthickness=1,
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        # 일반 Return과 숫자패드 Enter(KP_Enter)를 입력창에 직접 건다.
        for seq in ("<Return>", "<KP_Enter>"):
            self.entry.bind(seq, self._on_enter)
        bind_text_edit_shortcuts(self.entry)
        self.entry.focus_set()
        tk.Button(self.entry_row, text="해석", command=self.on_submit).pack(
            side="left", padx=(8, 0)
        )
        tk.Button(self.entry_row, text="초기화", command=self.on_reset).pack(
            side="left", padx=(6, 0)
        )

        self.toast = tk.Label(self.container, text="", font=self.theme.font("small"))
        self.toast.pack()

        self.result_frame = tk.Frame(self.container, padx=16, pady=8)
        self._result_shown = False

    def _build_menu(self):
        """표준 편집 메뉴(잘라내기/복사/붙여넣기/전체선택).

        macOS(Aqua)는 Cmd 클립보드 단축키를 위젯 바인딩이 아니라 메뉴로
        라우팅한다. 이 메뉴가 있어야 입력창에서 Cmd+C/V/X/A가 동작한다.
        각 항목은 현재 포커스 위젯에 표준 가상이벤트를 보낸다.
        """
        def emit(virtual):
            widget = self.root.focus_get()
            if widget is not None:
                widget.event_generate(virtual)

        menubar = tk.Menu(self.root)
        edit = tk.Menu(menubar, tearoff=0)
        edit.add_command(label="잘라내기", accelerator="Cmd+X",
                         command=lambda: emit("<<Cut>>"))
        edit.add_command(label="복사", accelerator="Cmd+C",
                         command=lambda: emit("<<Copy>>"))
        edit.add_command(label="붙여넣기", accelerator="Cmd+V",
                         command=lambda: emit("<<Paste>>"))
        edit.add_separator()
        edit.add_command(label="전체 선택", accelerator="Cmd+A",
                         command=lambda: emit("<<SelectAll>>"))
        menubar.add_cascade(label="편집", menu=edit)
        self.root.config(menu=menubar)

    # ---- 테마 ----
    def _apply_theme(self):
        """분석 결과는 그대로 두고, 화면 표현만 현재 시스템 테마에 맞춘다."""
        t = self.theme
        self.root.configure(bg=t.c("bg"))
        for frame in (self.container, self.input_frame, self.entry_row,
                      self.result_frame):
            frame.configure(bg=t.c("bg"))
        self.hint.configure(bg=t.c("bg"), fg=t.c("muted"))
        self.toast.configure(bg=t.c("bg"), fg=t.c("success"))
        self.entry.configure(
            bg=t.c("entry_bg"), fg=t.c("entry_fg"),
            insertbackground=t.c("entry_fg"),
            highlightbackground=t.c("border"), highlightcolor=t.c("accent"),
        )
        self._rerender()  # 테마 변경은 해석 재계산이 아니라 같은 결과의 재표현이다.
        # tk.Button은 macOS에서 네이티브 외관이라 시스템 테마를 자동 반영한다.

    def _watch_theme(self):
        mode = detect_mode()
        if mode != self.theme.mode:
            self.theme = Theme(mode)
            self._apply_theme()
            self._refit()
        self.root.after(1500, self._watch_theme)

    # ---- 동작 ----
    def _on_enter(self, _event=None):
        # 입력창이 처리하면 "break"로 전파를 끊어 루트 바인딩과 중복 실행되지 않게 한다.
        self.on_submit()
        return "break"

    def on_submit(self):
        # 버튼/Enter 입력은 모두 같은 파이프라인을 타게 해 시연 결과가 흔들리지 않게 한다.
        analysis = analyze(self.entry.get(), self.model, self.recommender)
        self._last = analysis if analysis is not None else _EMPTY
        self._rerender()
        self._show_result_frame()
        self._refit()  # 결과 크기에 맞춰 아래로 확장

    def on_reset(self):
        """입력과 결과를 지우고 다시 작은 입력창 상태로 되돌린다."""
        # 포커스를 잠깐 뗐다 되돌려 한글 IME 조합 버퍼를 비운다.
        # (조합 중이던 마지막 글자가 다음 입력 앞에 끼어들어 '트테스트'처럼 되는 것 방지)
        self.root.focus_set()
        self.root.update_idletasks()  # 포커스 아웃(=IME 조합 정리)이 반영되게 한다
        self.entry.delete(0, "end")
        self._last = None
        self._clear_results()
        self.result_frame.pack_forget()
        self._result_shown = False
        self.toast.config(text="")
        self.entry.focus_set()
        self._refit()  # 작은 창으로 축소

    def _show_result_frame(self):
        if not self._result_shown:
            self.result_frame.pack(fill="both", expand=True)
            self._result_shown = True

    def _refit(self):
        """창 크기를 현재 내용에 맞게 다시 맞춘다(확장/축소)."""
        self.root.update_idletasks()
        self.root.geometry("")

    # ---- 렌더링 ----
    def _clear_results(self):
        for child in self.result_frame.winfo_children():
            child.destroy()

    def _rerender(self):
        """저장된 분석 상태를 현재 화면 조건에 맞춰 다시 표현한다."""
        self._clear_results()
        if self._last is None:
            return
        t = self.theme
        if self._last is _EMPTY:
            tk.Label(
                self.result_frame, text="한국어 짧은 표현을 입력해주세요.",
                bg=t.c("bg"), fg=t.c("danger"), font=t.font("empty"),
            ).pack(anchor="w")
            return
        self._render(self._last)

    def _render(self, analysis: Analysis):
        t = self.theme
        rec = analysis.recommendation
        tie = rec.tie

        # 해석 이유가 핵심이므로, 부가 표시물인 카모지보다 위에 먼저 보여준다.
        self._render_reasons(analysis.explanation)

        if len(tie) >= 2:
            # 동점은 억지로 하나를 고르지 않고, 규칙 기반 모델의 모호함을 그대로 보여준다.
            tk.Label(
                self.result_frame, text="점수가 동점이라 두 인상 축을 함께 보여줍니다",
                bg=t.c("bg"), fg=t.c("muted"), font=t.font("hint"),
            ).pack(anchor="w", pady=(0, 6))
            columns = tk.Frame(self.result_frame, bg=t.c("bg"))
            columns.pack(fill="x")
            for index, (category, kaomoji) in enumerate(tie[:2]):
                self._render_column(columns, category, kaomoji, side="left")
                if index == 0:
                    tk.Frame(columns, width=2, bg=t.c("border")).pack(
                        side="left", fill="y", padx=14
                    )
        else:
            self._render_column(
                self.result_frame, rec.primary_category, rec.primary_kaomoji
            )

        if rec.secondary_categories:
            tk.Label(
                self.result_frame,
                text="다른 해석 후보: " + ", ".join(rec.secondary_categories),
                bg=t.c("bg"), fg=t.c("muted"), font=t.font("secondary"),
            ).pack(anchor="w", pady=(8, 0))

    def _render_column(self, parent, category, kaomoji, side="top"):
        t = self.theme
        column = tk.Frame(parent, bg=t.c("bg"))
        column.pack(side=side, anchor="n", fill="x", expand=True)
        tk.Label(
            column, text=f"[{category}]", bg=t.c("bg"), fg=t.c("text"),
            font=t.font("category"),
        ).pack(anchor="w")
        for size in SIZES:
            for text in kaomoji.get(size) or []:
                label = tk.Label(
                    column, text=text, bg=t.c("surface"), fg=t.c("text"),
                    font=t.kaomoji_font(size), padx=10, pady=4,
                    highlightthickness=1, highlightbackground=t.c("border"),
                    cursor="hand2",
                )
                label.pack(anchor="w", pady=3, fill="x")
                label.bind("<Button-1>", lambda _e, x=text: self._copy(x))

    def _render_reasons(self, explanation: Explanation):
        t = self.theme
        box = tk.Frame(self.result_frame, bg=t.c("bg"))
        box.pack(fill="x", pady=(0, 10))
        tk.Label(
            box, text="해석 이유", bg=t.c("bg"), fg=t.c("text"),
            font=t.font("section"),
        ).pack(anchor="w")
        for reason in explanation.reasons:
            tk.Label(
                box, text="• " + reason, bg=t.c("bg"), fg=t.c("text"),
                font=t.font("reason"), justify="left", wraplength=360,
            ).pack(anchor="w")
        if explanation.note:
            tk.Label(
                box, text="※ " + explanation.note, bg=t.c("bg"),
                fg=t.c("note"), font=t.font("small"),
                wraplength=360, justify="left",
            ).pack(anchor="w", pady=(4, 0))

    def _copy(self, text: str):
        # 표시 결과를 바로 붙여 넣어 볼 수 있게 하는 UI 편의 기능이며 점수에는 관여하지 않는다.
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.toast.config(text=f"복사됨: {text}")
        self.root.after(1500, lambda: self.toast.config(text=""))


def main():
    if tk.TkVersion < 8.6:
        print(
            f"[경고] Tk {tk.TkVersion} 감지됨. macOS 기본 Python(3.9)의 Tk 8.5는 "
            "다크 모드에서 GUI가 깨집니다. Tk 8.6+ Python(예: uv python install 3.13)을 "
            "쓰세요. 자세한 내용은 README의 '실행' 참고.",
            file=sys.stderr,
        )
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(
            "[오류] Tk GUI를 시작할 수 없습니다. Tcl/Tk 런타임이 없거나 Python이 "
            "TCL_LIBRARY/TK_LIBRARY 경로를 찾지 못한 상태입니다. README의 '실행' "
            "섹션에서 Tk 런타임 확인 방법을 참고하세요.",
            file=sys.stderr,
        )
        print(f"[원인] {exc}", file=sys.stderr)
        return 1
    KaomojiApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
