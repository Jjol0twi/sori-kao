# 재구현 목표 프롬프트: 기획서 기준 규칙 기반 카모지 추천 앱

아래 프롬프트는 현재 프로젝트를 기획서 기준으로 다시 만들거나, 구현이 크게
흐트러졌을 때 처음부터 재정렬하는 용도로 사용한다. 핵심 기준 문서는
`docs/development-goal.md`이며, 구현 세부 계약은 `docs/design.md`를 따른다.

```text
당신은 Python 개발자다. 이 저장소의 목표는 "한국어 음운 특징과 관습 표현을
활용한 규칙 기반 카모지 추천 앱"을 기획서에 맞춰 다시 구현하는 것이다.

가장 중요한 기준은 docs/development-goal.md다. 이 프로젝트는 사용자의 실제
감정을 맞히는 감정 판정기가 아니다. 한국어 입력의 소리 인상, 반복, 문장부호,
일부 관습 표현 보조 신호를 규칙과 NumPy 점수로 합산해 카모지 후보를 추천하고,
추천 이유를 설명하는 학습용 Python 앱이다.

반드시 먼저 읽을 문서:
1. docs/development-goal.md
   - 프로젝트 목표, 배경, 범위, 제외 기능, 한계, 평가 기준의 최상위 기준이다.
2. docs/design.md
   - 14차원 feature vector, 점수식, JSON 스키마, 신뢰도, GUI 흐름의 구현 계약이다.
3. README.md
   - 실행 방법, 현재 프로젝트 구조, 한계 설명을 확인한다.
4. docs/review-refactor-prompt.md
   - 구현 후 재검토할 때의 점검 기준이다.
5. docs/git-conventions.md
   - 커밋 메시지와 작은 단위 커밋 규칙이다.
6. docs/build-prompt.md
   - 파일이 있으면 보조 구현 지시로만 참고한다. development-goal.md와 design.md가 우선이다.

절대 지켜야 할 방향:
- 생성형 AI, LLM, OpenAI API, 외부 API, 네트워크 호출을 사용하지 않는다.
- 추천 경로는 오프라인에서 재현 가능해야 하며, random을 쓰지 않는다.
- 외부 의존성은 NumPy만 둔다. GUI는 tkinter를 사용한다.
- 카모지와 가중치는 data/*.json에서 읽고, 코드에 하드코딩하지 않는다.
- 논문과 참고자료는 "특징 선택 근거"로만 사용한다. category weight 숫자,
  bias, confidence threshold, bonus 값은 논문 수치가 아니라 heuristic_initial 또는
  developer_defined로 취급한다.
- "카카오톡보다 좋은 추천"이라고 구현하거나 설명하지 않는다. 카카오톡은 입력 중
  추천 UX 참고 사례일 뿐이며, 이 프로젝트의 강점은 투명성, 오프라인 재현성,
  규칙 실험 가능성이다.
- 결과는 감정 정답이 아니라 카모지 후보 순위다. 낮은 신뢰도 입력에서는 강하게
  단정하지 않는다.

MVP에 포함할 기능:
1. tkinter GUI
   - 한국어 단어/문장을 입력받는다.
   - 추천 버튼 또는 Enter로 분석한다.
   - 결과 영역에 1위 카테고리의 카모지를 작음/보통/큼으로 보여준다.
   - 보조 후보와 추천 이유를 함께 보여준다.
   - 입력창 기본 편집 동작(Cmd/Ctrl A/C/V/X)을 보장한다.
2. 한글 분해
   - 완성형 한글 음절만 초성·중성·종성으로 분해한다.
   - 호환 자모, 문장부호, 영문, 숫자, 이모지는 별도 처리한다.
3. 전처리
   - 완성형 음절, 단독 자모, 반복 대상 문자, 문장부호 카운트를 분리한다.
   - ㅋㅋ/ㅠㅠ 같은 자모는 음운 벡터가 아니라 관습 표현 보조 신호로 다룬다.
4. 14차원 feature vector
   - feature_order는 docs/design.md와 data/category_weights.json이 일치해야 한다.
   - 모든 feature 값은 [0, 1] 범위로 정규화한다.
   - 긴 문장이 count 특징 때문에 점수를 지배하지 않도록 ratio를 사용한다.
5. NumPy 점수 모델
   - 점수식은 category_scores = x @ W.T + bias + auxiliary_bonus다.
   - 10개 카테고리 순서는 응원, 기쁨, 당황, 분노, 긴장, 피곤, 장난, 사과, 감사, 집중이다.
   - 동점은 카테고리 순서로 안정적으로 처리한다.
6. 보조 신호
   - auxiliary_keywords는 명시적 감사/사과/응원/집중 같은 표현만 제한적으로 보정한다.
   - 자모 반복은 별도 보조 신호로 처리한다. 특히 ㅋ 반복은 장난 보조 신호로 둔다.
   - semantic_hints는 하암, 아프다, 힘들어, 이런, 망할처럼 음운만으로 구분하기 어려운
     표현을 중간 태그로 정규화한다. 단어를 무작정 최종 카테고리에 직접 꽂는 예외 목록으로
     만들지 않는다.
7. 신뢰도
   - 짧은 입력, 점수 차이가 작은 입력, 보조 신호가 음운 점수보다 큰 입력은 low로 표시한다.
   - low 결과는 실패를 숨기는 장치가 아니라 과도한 확신을 피하는 안전장치다.
8. 추천 이유
   - 실제 점수에 기여한 feature와 보조 신호만 설명에 사용한다.
   - "기쁨입니다"처럼 단정하지 말고 "점수가 반영되었습니다", "후보로 추천되었습니다"처럼 표현한다.
9. 로컬 카모지 카탈로그
   - data/kaomoji_catalog.json에 카테고리별 카모지를 저장한다.
   - 각 카테고리에 작음/보통/큼 후보가 있어야 한다.
   - 같은 입력은 항상 같은 카모지를 보여준다.

MVP에서 제외할 기능:
- 생성형 AI/API/LLM 사용
- 사용자별 추천 개인화
- 카카오톡 UI 복제
- 실제 카카오톡 이모티콘 상품 추천
- 대규모 학습 데이터 수집 또는 딥러닝 모델 학습
- 자음/모음 교체 자동 탐지
- 모바일 앱 배포
- 추천 결과의 심리학적 정확성 보장

재구현 작업 순서:
1. 먼저 git status를 확인하고, 기존 사용자 변경을 되돌리지 않는다.
2. docs/development-goal.md와 docs/design.md를 끝까지 읽고, 구현해야 할 계약을 요약한다.
3. 현재 코드와 데이터가 문서와 충돌하는 지점을 먼저 목록화한다.
4. 충돌이 있으면 development-goal.md를 최우선 기준으로 삼고, design.md의 구체 구현 규칙을 따른다.
   문서 자체가 모순이면 먼저 보고하고 최소 수정만 제안한다.
5. 다음 모듈 경계를 유지하며 재구현한다.
   - hangul_decomposer.py: 한글 완성형 음절 분해
   - text_preprocessor.py: 입력 분류와 보조 신호 재료 분리
   - feature_extractor.py: 14차원 feature vector
   - scoring_model.py: NumPy 점수, Top-3, confidence, auxiliary/semantic hints
   - recommender.py: 결정적 카모지 선택
   - explanation.py: 실제 기여도 기반 추천 이유
   - theme.py: GUI 색상과 폰트 토큰
   - app.py: tkinter GUI와 전체 흐름 연결
6. data/category_weights.json과 data/kaomoji_catalog.json은 코드와 분리해 유지한다.
7. 테스트를 먼저 읽고, 필요한 경우 테스트를 강화한 뒤 구현한다.
8. 한 변경 단위가 끝날 때마다 uv run --with pytest python -m pytest를 실행한다.
9. 커밋은 docs/git-conventions.md에 따라 작은 단위로 만든다. AI/도구 공동작성 트레일러는 넣지 않는다.

반드시 직접 확인할 대표 입력:
- 아싸아싸!!
- ㅋㅋㅋㅋ 뭐야
- ㄹㅇㅋㅋ
- 으으... 힘들다
- 고마워요ㅎㅎ
- 죄송합니다...
- 빠샤 집중하자
- 하암
- 맘이 아프다
- 힘들어
- 이런
- 망할
- 구르구르
- 가지마
- 화나
- 피곤하다
- 아프다
- 배고파
- 놀랐잖아
- ㅠㅠㅠ

확인 기준:
- 모든 feature 값이 [0, 1] 범위인지 확인한다.
- feature_order가 코드, JSON, 문서에서 일치하는지 확인한다.
- category_weights.json의 _meta에 weights_source, bias_source, auxiliary/semantic cap,
  confidence 설정이 들어 있는지 확인한다.
- 추천 이유가 실제 contribution 또는 auxiliary source와 일치하는지 확인한다.
- semantic_hints가 쓰인 결과는 순수 음운 추천처럼 보이지 않게 낮은 신뢰도 또는 보조 신호 설명을 포함한다.
- `가지마`처럼 밝은 모음 때문에 감사 후보로 흐르기 쉬운 관습 요청은 높은 신뢰도 감사로 단정하지 않는다.
- `화나`, `피곤하다`, `아프다`, `배고파`, `놀랐잖아`처럼 밝은 모음이 많은 반례가 응원·기쁨·감사 high로 쏠리지 않는지 확인한다.
- `ㅠㅠㅠ` 같은 자모만 반복된 입력은 장난 high로 단정하지 않는다.
- 짧거나 모호한 입력은 높은 확신으로 보이지 않게 한다.
- 외부 API 호출, random, 네트워크 의존이 추천 경로에 없어야 한다.

완료 기준:
- uv run --with pytest python -m pytest가 통과한다.
- GUI가 uv run python app.py로 실행된다.
- README의 실행 방법과 실제 실행 방법이 일치한다.
- docs/development-goal.md의 MVP 범위와 제외 기능을 벗어나지 않는다.
- docs/design.md의 feature vector, 점수식, confidence, JSON 스키마와 코드가 일치한다.
- 테스트 입력의 기대 카테고리가 대체로 Top-3에 들어오되, 이를 심리학적 정확도로 주장하지 않는다.
- 최종 보고에는 수정한 파일, 바꾼 이유, 실행한 테스트, 남은 한계를 짧게 적는다.
```
