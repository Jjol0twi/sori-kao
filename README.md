# sori-kao

> 한국어 단어/문장의 **소리 느낌(음운 특징)** 과 일부 **관습 표현 보조 신호**를 분석해 어울리는 **기호 카모지 후보**를 추천하고, **그 이유까지 설명**하는 Python 앱.
> Rule-based, explainable kaomoji recommender driven by Korean phonetic symbolism — no AI/LLM, fully offline.

## 무엇을 하는가

`아싸`, `으으`, `ㅋㅋㅋ`, `하...`, `빠샤`처럼 감정 단어가 없어도, 입력의 소리와 형태(밝은/어두운 모음, 된소리·거센소리, 받침, 반복, 문장부호)를 수치화해 카모지 추천 카테고리의 후보 점수를 계산한다. `하암`, `ㅋㅋ`, `ㅠㅠ`처럼 관습성이 강한 표현은 음운 특징만으로 구분하기 어려우므로 보조 신호로만 반영한다.

```
입력:  아싸아싸!!
추천:  (ง •̀ω•́)ง         (응원)
이유:
- 같은 음절 패턴이 반복되어 강조·리듬 점수가 올라갔습니다.
- 밝은 모음 비율이 높아 긍정적 인상 점수가 반영되었습니다.
- 느낌표가 감지되어 에너지 점수가 보정되었습니다.
```

## 특징

- **규칙 기반 + 설명 가능**: 생성형 AI/LLM/외부 API를 쓰지 않고, 사람이 정한 규칙과 NumPy 점수 계산으로만 동작한다. 왜 추천했는지를 규칙 단위로 보여준다.
- **오프라인 재현성**: 외부 네트워크 호출 없이 로컬 JSON 데이터만으로 실행되며, 같은 입력은 항상 같은 결과를 낸다.
- **음운 특징 중심**: 단순 키워드 매칭이 아니라 14차원 음운 특징 벡터로 10개 카테고리(응원·기쁨·당황·분노·긴장·피곤·장난·사과·감사·집중)의 Top-3를 계산한다. 관습 표현은 별도 보조 규칙으로 처리해 음운 점수와 구분한다.
- **감정 판정기가 아님**: 추천 결과는 사용자의 실제 감정 정답이 아니라, 소리 인상과 보조 신호를 합산한 카모지 후보 순위다.

> 카카오톡 이모티콘 추천의 "맥락 기반 추천" 아이디어는 참고하되, 상업적·개인화 추천이 아니라 **추천 과정을 분해해 설명할 수 있는** 학습용 프로젝트를 지향한다. 강점은 추천 품질이 아니라 규칙의 투명성·오프라인 재현성·실험 가능성이다.

## 처리 흐름

```
입력 → 전처리 → 한글 분해 → 음운 특징 추출(14차원)
     → 보조 신호 탐지(키워드·자모·의미 힌트)
     → NumPy 점수 계산 → Top-3 후보 카테고리 → 카모지 추천 → 추천 이유 출력
```

## 프로젝트 구조

```
sori-kao/
├── pyproject.toml            # Python/NumPy 의존성 선언
├── uv.lock                   # uv 의존성 잠금 파일
├── app.py                    # tkinter GUI + 전체 흐름
├── theme.py                  # GUI 색상·폰트·여백 테마
├── hangul_decomposer.py      # 한글 음절 → 초성·중성·종성
├── text_preprocessor.py      # 입력 분류(음절/자모/부호/기타)
├── feature_extractor.py      # 14차원 음운 특징 벡터
├── scoring_model.py          # NumPy 점수 + Top-3 + 신뢰도
├── recommender.py            # 점수 → 카모지 선택(결정적)
├── explanation.py            # 추천 이유 생성
├── data/
│   ├── category_weights.json # 특징 가중치·bias·보조 키워드·임계값
│   └── kaomoji_catalog.json  # 카테고리별 카모지(+size)
├── tests/                    # 분해·특징·점수·회귀 단위 테스트
└── docs/
    ├── development-goal.md    # 기획서
    ├── design.md             # 설계서
    ├── review-refactor-prompt.md # 검토·리팩터링 프롬프트
    ├── rebuild-goal-prompt.md # 기획서 기준 재구현 목표 프롬프트
    ├── build-prompt.md       # 구현 지시 프롬프트(로컬 내부 문서)
    └── git-conventions.md    # 커밋 컨벤션
```

## 상태

MVP 구현 완료. 한글 분해부터 tkinter GUI까지 동작하며, 단위·회귀 테스트가 통과한다.

## 실행

> **Python 버전 (중요)** — GUI는 **Tk 8.6 이상**이 필요하다. **Python 3.11 이상**을 쓴다(이 저장소는 3.13 기준, `.python-version`에 고정).
> macOS 기본 `python3`(3.9)는 **Tk 8.5**라 다크 모드에서 입력창·레이아웃이 깨진다. 실행 시
> `The system version of Tk is deprecated` 경고가 뜨면 이 경우다 — 아래 방법으로 새 Python을 쓴다.

### uv 사용 (권장)

`.python-version`(3.13) 덕분에 uv가 Python 버전을 자동 선택한다. 다만 Tk 모듈 버전만 맞아도 로컬 Tcl/Tk 런타임(`init.tcl`)이 빠져 있으면 GUI가 뜨지 않을 수 있으므로, 처음 실행 전 루트 생성까지 확인한다.

```bash
uv python install 3.13      # 처음 한 번(이미 있으면 생략)
uv venv                     # .python-version(3.13)으로 .venv 생성
uv run python -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy(); print(tk.TkVersion)"
uv run python app.py
```

NumPy는 `pyproject.toml`의 프로젝트 의존성으로 설치된다.
이미 GUI 창이 떠 있다면 기존 창을 완전히 종료한 뒤 다시 `uv run python app.py`를 실행해야 최신 JSON/코드 변경이 반영된다.
입력창 편집 단축키는 macOS `Cmd+A/C/V/X`, Windows/Linux `Ctrl+A/C/V/X`를 지원한다.
`Can't find a usable init.tcl` 오류가 나오면 Python 모듈은 있어도 Tcl/Tk 런타임 파일을 못 찾는 상태다. 이 경우 python.org 설치본(Tk 포함)을 쓰거나 Homebrew의 `tcl-tk`/`python-tk` 설치 상태를 확인한 뒤 가상환경을 다시 만든다.

### uv를 안 쓰는 경우

[python.org 설치본](https://www.python.org/downloads/)(Tk 8.6 포함)이나 `brew install python-tk`로 받은 Python을 쓴다.
**시스템 `python3`(3.9)로는 GUI가 정상 표시되지 않는다.**

```bash
python3.13 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install numpy && python app.py
```

표준 라이브러리 tkinter와 NumPy 외 의존성은 없다. GUI 실행에는 디스플레이와 정상 설치된 Tcl/Tk 런타임이 필요하다.
Tk 실행 확인: `python -c "import tkinter as tk; root=tk.Tk(); root.withdraw(); root.destroy(); print(tk.TkVersion)"` → **8.6 이상**이어야 한다.

### 테스트

```bash
uv run --with pytest python -m pytest
# 또는 venv 활성화 후: pip install numpy pytest && python -m pytest
```

## 한계

- 음운 특징과 감정의 관계는 **절대 규칙이 아니라 경향**이다. 추천 이유는 감정 판정이 아니라 점수 계산 근거를 보여주는 설명이다.
- `죄송`처럼 입력이 짧거나 키워드에 크게 의존하는 입력은 기대 카테고리가 1위에 안 들 수 있다. 이런 입력은 **낮은 신뢰도**로 표시한다.
- `하암`, `가지마`, `화나`, `놀랐잖아`, `아프다`, `피곤하다`, `배고파`처럼 소리 특징만으로 뜻을 구분하기 어려운 표현은 `semantic_hints`의 중간 태그로 보정하되, 낮은 신뢰도로 표시한다.
- `구르구르` 같은 반복 의태어가 모두 피곤으로 쏠리지 않고, `ㅠㅠㅠ` 같은 자모 반복이 장난으로 묻히지 않도록 반복은 감정 정답이 아니라 강조·리듬 신호로만 다룬다.
- 회귀 테스트는 심리학적 정확도 검증이 아니라, 설계한 규칙과 구현 결과가 대체로 일치하는지 확인하기 위한 용도다.

## 문서

- [기획서](docs/development-goal.md) — 배경·차별점·MVP 범위·반례·평가 기준
- [설계서](docs/design.md) — 분해/특징/점수/신뢰도/데이터 스키마/GUI 명세
- [검토·리팩터링 프롬프트](docs/review-refactor-prompt.md) — 구현 검토와 재정렬 기준
- [재구현 목표 프롬프트](docs/rebuild-goal-prompt.md) — 기획서 기준 재구현·검증 절차
- [구현 프롬프트](docs/build-prompt.md) — 위 문서를 구현 계약으로 정리
- [커밋 컨벤션](docs/git-conventions.md) — Conventional Commits 규칙

## 라이선스

[Apache License 2.0](LICENSE) © 2026 imtsoftai
