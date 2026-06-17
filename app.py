"""tkinter GUI와 전체 추천 흐름(build-prompt §13).

초기에는 입력창 + 추천(Enter) + 초기화 버튼만 있는 작은 창이 뜬다.
입력이 확정되면 창이 아래로 확장되며 1위 카테고리의 카모지(작음/보통/큼)와
추천 이유·보조 후보를 보여준다. 1위가 동점이면 결과를 세로 두 열로 나눠
각 감정의 카모지를 나란히 보여준다.

색·폰트는 theme.py의 디자인 시스템 토큰을 따르며, 시스템 라이트/다크
모드에 자동으로 반응한다(설정 없이 실시간 재적용).
"""

import sys
import tkinter as tk
from dataclasses import dataclass

from explanation import Explanation, build_explanation
from recommender import KaomojiRecommender, Recommendation, SIZES
from scoring_model import ScoringModel, ScoreResult
from theme import Theme, detect_mode

_EMPTY = "empty"  # 빈 입력 상태 표식


@dataclass
class Analysis:
    score: ScoreResult
    recommendation: Recommendation
    explanation: Explanation


def analyze(text: str, model: ScoringModel, recommender: KaomojiRecommender):
    """입력을 분석해 점수·추천·이유를 묶어 반환한다. 빈 입력은 ``None``."""
    if not text.strip():
        return None
    score = model.score(text)
    return Analysis(score, recommender.recommend(score), build_explanation(score))


class KaomojiApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.model = ScoringModel()
        self.recommender = KaomojiRecommender()
        self.theme = Theme(detect_mode())
        self._last = None  # None | _EMPTY | Analysis

        root.title("sori-kao — 음운 카모지 추천")
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
            self.input_frame, text="한국어 단어나 문장을 입력하세요",
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
        self.entry.focus_set()
        tk.Button(self.entry_row, text="추천", command=self.on_submit).pack(
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
        """현재 테마 토큰을 정적 위젯에 칠하고 결과를 다시 그린다."""
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
        self._rerender()  # 결과가 떠 있으면 새 테마로 다시 그린다
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
        """self._last 상태를 현재 테마로 결과 영역에 다시 그린다."""
        self._clear_results()
        if self._last is None:
            return
        t = self.theme
        if self._last is _EMPTY:
            tk.Label(
                self.result_frame, text="한국어 단어나 문장을 입력해주세요.",
                bg=t.c("bg"), fg=t.c("danger"), font=t.font("empty"),
            ).pack(anchor="w")
            return
        self._render(self._last)

    def _render(self, analysis: Analysis):
        t = self.theme
        rec = analysis.recommendation
        tie = rec.tie

        if len(tie) >= 2:
            tk.Label(
                self.result_frame, text="점수가 동점이라 두 카테고리를 함께 보여줍니다",
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
                text="보조 후보: " + ", ".join(rec.secondary_categories),
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
            box, text="추천 이유", bg=t.c("bg"), fg=t.c("text"),
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
    root = tk.Tk()
    KaomojiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
