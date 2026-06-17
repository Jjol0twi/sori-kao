"""tkinter GUI와 전체 추천 흐름(build-prompt §13).

초기에는 입력창 + 추천(Enter) + 초기화 버튼만 있는 작은 창이 뜬다.
입력이 확정되면 창이 아래로 확장되며 1위 카테고리의 카모지(작음/보통/큼)와
추천 이유·보조 후보를 보여준다. 1위가 동점이면 결과를 세로 두 열로 나눠
각 감정의 카모지를 나란히 보여준다. 초기화 버튼은 입력과 결과를 지우고
다시 작은 입력창 상태로 되돌린다.
"""

import tkinter as tk
from dataclasses import dataclass

from explanation import Explanation, build_explanation
from recommender import KaomojiRecommender, Recommendation, SIZES
from scoring_model import ScoringModel, ScoreResult


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
    SIZE_FONTS = {"작음": 16, "보통": 24, "큼": 34}
    BG = "#fafafa"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.model = ScoringModel()
        self.recommender = KaomojiRecommender()

        root.title("sori-kao — 음운 카모지 추천")
        root.configure(bg=self.BG)
        root.geometry("480x150")  # 시작 시 작은 창(이후 내용에 맞춰 재조정)

        # 시스템 다크모드와 무관하게 밝은 배경을 보장하는 컨테이너
        container = tk.Frame(root, bg=self.BG)
        container.pack(fill="both", expand=True)
        self.container = container

        input_frame = tk.Frame(container, bg=self.BG, padx=16, pady=14)
        input_frame.pack(fill="x")

        tk.Label(
            input_frame, text="한국어 단어나 문장을 입력하세요",
            bg=self.BG, fg="#555", font=("", 11),
        ).pack(anchor="w")

        entry_row = tk.Frame(input_frame, bg=self.BG)
        entry_row.pack(fill="x", pady=(6, 0))
        # 다크모드에서도 보이도록 흰 배경·검은 글자를 명시
        self.entry = tk.Entry(
            entry_row, font=("", 15), width=24,
            bg="white", fg="#111", insertbackground="#111",
            relief="solid", borderwidth=1,
            highlightthickness=1, highlightbackground="#bbb",
            highlightcolor="#4a90d9",
        )
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Return>", lambda _e: self.on_submit())
        self.entry.focus_set()
        tk.Button(
            entry_row, text="추천", command=self.on_submit, font=("", 12),
        ).pack(side="left", padx=(8, 0))
        tk.Button(
            entry_row, text="초기화", command=self.on_reset, font=("", 12),
        ).pack(side="left", padx=(6, 0))

        self.toast = tk.Label(container, text="", bg=self.BG, fg="#2a7", font=("", 10))
        self.toast.pack()

        # 결과 영역(처음에는 숨김; 첫 추천 때 pack)
        self.result_frame = tk.Frame(container, bg=self.BG, padx=16, pady=8)
        self._result_shown = False

        # 창이 화면에 그려진 뒤 입력창 크기에 맞춰 작게 맞춘다(macOS 타이밍)
        self.root.after(120, self._refit)

    # ---- 동작 ----
    def on_submit(self):
        analysis = analyze(self.entry.get(), self.model, self.recommender)
        for child in self.result_frame.winfo_children():
            child.destroy()

        if analysis is None:
            tk.Label(
                self.result_frame, text="한국어 단어나 문장을 입력해주세요.",
                bg=self.BG, fg="#c33", font=("", 12),
            ).pack(anchor="w")
        else:
            self._render(analysis)
        self._show_result_frame()
        self._refit()  # 결과 크기에 맞춰 아래로 확장

    def on_reset(self):
        """입력과 결과를 지우고 다시 작은 입력창 상태로 되돌린다."""
        self.entry.delete(0, "end")
        for child in self.result_frame.winfo_children():
            child.destroy()
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

    def _render(self, analysis: Analysis):
        rec = analysis.recommendation
        tie = rec.tie

        if len(tie) >= 2:
            tk.Label(
                self.result_frame, text="점수가 동점이라 두 카테고리를 함께 보여줍니다",
                bg=self.BG, fg="#555", font=("", 11),
            ).pack(anchor="w", pady=(0, 6))
            columns = tk.Frame(self.result_frame, bg=self.BG)
            columns.pack(fill="x")
            for index, (category, kaomoji) in enumerate(tie[:2]):
                self._render_column(columns, category, kaomoji, side="left")
                if index == 0:
                    tk.Frame(columns, width=2, bg="#ddd").pack(
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
                bg=self.BG, fg="#777", font=("", 11),
            ).pack(anchor="w", pady=(8, 0))

    def _render_column(self, parent, category, kaomoji, side="top"):
        column = tk.Frame(parent, bg=self.BG)
        column.pack(side=side, anchor="n", fill="x", expand=True)
        tk.Label(
            column, text=f"[{category}]", bg=self.BG, fg="#333",
            font=("", 13, "bold"),
        ).pack(anchor="w")
        for size in SIZES:
            text = kaomoji.get(size)
            if not text:
                continue
            label = tk.Label(
                column, text=text, bg="white", fg="#111",
                font=("", self.SIZE_FONTS[size]), padx=10, pady=4,
                relief="solid", borderwidth=1, cursor="hand2",
            )
            label.pack(anchor="w", pady=3, fill="x")
            label.bind("<Button-1>", lambda _e, t=text: self._copy(t))

    def _render_reasons(self, explanation: Explanation):
        box = tk.Frame(self.result_frame, bg=self.BG)
        box.pack(fill="x", pady=(10, 0))
        tk.Label(
            box, text="추천 이유", bg=self.BG, fg="#333", font=("", 12, "bold"),
        ).pack(anchor="w")
        for reason in explanation.reasons:
            tk.Label(
                box, text="• " + reason, bg=self.BG, fg="#444",
                font=("", 11), justify="left", wraplength=360,
            ).pack(anchor="w")
        if explanation.note:
            tk.Label(
                box, text="※ " + explanation.note, bg=self.BG, fg="#a60",
                font=("", 10), wraplength=360, justify="left",
            ).pack(anchor="w", pady=(4, 0))

    def _copy(self, text: str):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.toast.config(text=f"복사됨: {text}")
        self.root.after(1500, lambda: self.toast.config(text=""))


def main():
    root = tk.Tk()
    KaomojiApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
