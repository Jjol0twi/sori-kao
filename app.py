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


def _safe_selection_present(entry):
    try:
        return entry.selection_present()
    except (tk.TclError, AttributeError):
        return False


def _safe_selection_text(entry):
    try:
        return entry.selection_get()
    except (tk.TclError, AttributeError, ValueError):
        return ""


def _delete_selection(entry):
    if not _safe_selection_present(entry):
        return
    try:
        entry.delete("sel.first", "sel.last")
    except (tk.TclError, AttributeError, ValueError):
        pass


def _make_text_edit_handler(action: str):
    def handler(event):
        entry = event.widget

        # macOS Tk 단축키가 런타임마다 달라 직접 처리해 입력 실험 흐름이 끊기지 않게 한다.
        if action == "a":
            entry.selection_range(0, "end")
            entry.icursor("end")
        elif action == "c":
            selected = _safe_selection_text(entry)
            if selected:
                entry.clipboard_clear()
                entry.clipboard_append(selected)
        elif action == "v":
            try:
                text = entry.clipboard_get()
            except (tk.TclError, AttributeError, ValueError):
                text = ""
            if text:
                _delete_selection(entry)
                entry.insert("insert", text)
        elif action == "x":
            selected = _safe_selection_text(entry)
            if selected:
                entry.clipboard_clear()
                entry.clipboard_append(selected)
                _delete_selection(entry)
        return "break"

    return handler


def bind_text_edit_shortcuts(entry, is_macos: bool = None):
    """테스트 문장을 빠르게 바꿔 넣을 수 있도록 기본 편집 동작을 보장한다."""
    if is_macos is None:
        is_macos = sys.platform == "darwin"

    modifiers = ["Control"]
    if is_macos:
        modifiers.append("Command")

    for modifier in modifiers:
        for key in _EDIT_SHORTCUTS:
            handler = _make_text_edit_handler(key)
            entry.bind(f"<{modifier}-{key}>", handler)
            entry.bind(f"<{modifier}-{key.upper()}>", handler)


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
        self.entry.bind("<Return>", lambda _e: self.on_submit())
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
    def on_submit(self):
        # 버튼/Enter 입력은 모두 같은 파이프라인을 타게 해 시연 결과가 흔들리지 않게 한다.
        analysis = analyze(self.entry.get(), self.model, self.recommender)
        self._last = analysis if analysis is not None else _EMPTY
        self._rerender()
        self._show_result_frame()
        self._refit()  # 결과 크기에 맞춰 아래로 확장

    def on_reset(self):
        """입력과 결과를 지우고 다시 작은 입력창 상태로 되돌린다."""
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

        self._render_reasons(analysis.explanation)

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
            text = kaomoji.get(size)
            if not text:
                continue
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
        box.pack(fill="x", pady=(10, 0))
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
