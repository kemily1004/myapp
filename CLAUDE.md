# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 상태

Streamlit 기반 쇼핑 리스트 웹앱(아이템 추가/수정/삭제/체크). `PROMPTS.md`의 1~4단계(뼈대 → 핵심 기능 → UI → Playwright 검토)를 모두 마쳤고, 4단계에서 찾은 버그는 아직 고치지 않았다(아래 "알려진 문제"). 배포도 아직 하지 않았다.
- `PRD.md`: 요구사항의 기준 문서. 기능 범위, 데이터 모델, 수용 기준(9.1), 비기능 요구사항(8, 예: 100개에서 1초 이내 반영)은 여기를 따른다.
- `PROMPTS.md`: 단계별 개발 프롬프트. 사용자가 단계를 지정해 요청하면 그 단계 범위를 넘어서 구현하지 말 것 (예: 3단계에서 기능 로직 변경 금지, 4단계는 보고만 하고 수정 금지).

## 명령어

```bash
pip install -r requirements.txt
streamlit run app.py
streamlit run app.py --server.headless true --server.port 8501   # Playwright 테스트용
```

별도의 빌드/린트/단위 테스트 설정은 없다. `.streamlit/config.toml`을 바꾸면 서버를 재시작해야 반영된다.

## 아키텍처

- `app.py`: UI와 상태 관리. `st.session_state["items"]`(아이템 리스트), `["editing_id"]`(편집 중인 항목, 동시에 1개), `["add_error"]`/`["edit_error"]`(경고 문구), `["confirm_clear_all"]`(전체 삭제 확인 단계), `["toast"]`(예약된 알림)를 쓴다.
- 코드 흐름: 콜백(`add_item`, `toggle_item`, `delete_item`, `save_edit` …)이 상태를 바꾸고 `set_items()`로 저장 → rerun 시 `render_*` 함수들이 화면을 그린다. 알림은 콜백에서 `queue_toast()`로 예약하고 `render_toast()`가 띄운다.
- 입력 검증은 `validate()` 한 곳에서 한다 (이름 공백 제거 후 1~50자, 수량 1~999). 추가와 수정이 같은 함수를 쓴다.
- `storage.py`: `load_items()` / `save_items(items)`만 노출한다. `app.py`는 이 두 함수만 호출해야 나중에 JSON → 외부 DB(Supabase, Google Sheets 등, v1.1)로 교체할 수 있다. 로드 시 파일이 없거나 손상되면 빈 리스트를 반환하고, 필드가 빠진 항목은 `_normalize()`로 기본값을 채운다 (id나 name이 없는 항목은 버림).
- 아이템 모델: `{id: uuid4 str, name: 1~50자, quantity: 1~999, checked: bool, created_at: ISO 8601}`.

## Streamlit 구현 규칙

- 세션 상태는 `st.session_state["items"]`처럼 대괄호로 접근한다. `st.session_state.items`는 dict의 `.items()` 메서드로 해석되어 오류가 난다.
- 위젯 key는 반드시 아이템 id 기반(`f"del_{item['id']}"`)으로. 리스트 인덱스를 key로 쓰면 삭제 후 다른 항목이 지워지거나 체크 상태가 뒤섞인다.
- 위젯 key를 세션 상태 이름과 겹치게 짓지 않는다 (예: 상태 `confirm_clear_all`과 버튼 key가 같으면 버튼이 상태값을 덮어씀. 그래서 버튼 key는 `confirm_clear_all_btn`).
- 상태 변경은 `on_click`/`on_change` 콜백에서 처리하고 item id를 인자로 넘긴다. 렌더링 반복문 안에서 리스트를 수정하지 않는다.
- 사용자 입력(아이템 이름)은 `escape_md()`로 이스케이프해서 렌더링하고(토스트 포함), 사용자 입력이 들어가는 곳에는 `unsafe_allow_html`을 쓰지 않는다.

## UI / 스타일

- 커스텀 CSS는 `app.py`의 `CUSTOM_CSS` 한 곳에만 두고, `st.container(key=...)`가 붙이는 `.st-key-<key>` 클래스로 범위를 한정한다 (`add_area`, `item_list`, `row_<id>` / 체크된 행은 `row_done_<id>`, `empty_state`, `clear_checked`, `clear_all`, `confirm_clear_all_btn`). 위젯 key나 컨테이너 key를 바꾸면 CSS 선택자와 Playwright 선택자도 같이 바꿀 것.
- 좁은 화면에서 `st.columns`가 세로로 쌓이는 것을 CSS(`flex-wrap: nowrap`)로 막고 있다. 행에 열을 추가하면 390px 너비에서 다시 확인할 것.
- `.streamlit/config.toml`에서 테마 색은 `[theme.light]` / `[theme.dark]`로 나눠 지정한다. `[theme]`에 직접 지정하면 다크 모드가 꺼진다.
- 배경/글자색을 하드코딩하지 않는다 (라이트/다크 모두 지원).

## 테스트

- **AppTest** (`streamlit.testing.v1`): 빠른 로직 확인용. 앱 폴더가 import 경로에 자동으로 들어가지 않으므로 `PYTHONPATH=.`가 필요하다. `clear_on_submit` 같은 브라우저 쪽 동작은 재현하지 못한다.
- **Playwright**: 최종 검증은 실행 중인 앱(http://localhost:8501)을 조작해서 한다. 테스트는 `data.json`을 덮어쓰므로 시작 전 백업하고 끝나면 복원한다 (원래 없었으면 삭제). 스크린샷은 Playwright MCP가 허용하는 경로인 `.playwright-mcp/`(gitignore됨)에 저장한다.
- Playwright 선택자 주의점:
  - 첫 로딩이나 새로고침 직후에는 목록이 다 그려지기까지 1~3초 걸린다. 고정 대기 대신 행 개수를 `waitForFunction`으로 기다릴 것.
  - 체크박스의 실제 `input`은 화면 밖에 있어 `check()`가 실패한다. `[data-testid="stCheckbox"] label`을 클릭한다.
  - `.st-key-<key> button`에는 보이지 않는(0×0) 버튼이 먼저 잡힐 수 있으므로 `button:visible`을 쓴다.
  - 추가 폼의 제출 버튼은 `.st-key-add_area [data-testid="stFormSubmitButton"] button`으로 잡는다. `.st-key-add_area button`은 수량 칸의 −/+ 버튼이 먼저 잡힌다.
  - 체크박스 숨김 라벨도 마크다운 컨테이너라서, 이름 칸 텍스트는 행의 두 번째 `stColumn`에서 읽는다.

## 알려진 문제 (4단계 검토 결과, 미수정)

1. **[높음]** 여러 탭/기기에서 동시에 쓰면 데이터가 사라진다. `init_state()`가 처음 한 번만 `load_items()`하고 `set_items()`가 세션의 리스트 전체로 파일을 덮어쓰기 때문.
2. [중간] 수량칸에 범위 밖 값(0, 1000, -5)을 넣으면 경고 없이 1로 바뀌거나, 항목이 추가되지 않고 "이름을 입력해 주세요" 경고가 뜬다 (`number_input`의 min/max 제한과 관련).
3. [중간] 삭제 버튼을 빠르게 두 번 누르면 아래 항목이 올라와 같이 삭제된다. 되돌리기 기능 없음.
4. [중간] 항목 100개에서 조작 반영에 약 1.2~1.3초 (PRD 8 기준 1초 초과). 매 rerun마다 모든 행을 다시 그리기 때문.
5. [낮음] 데이터에 중복 id가 있으면 `StreamlitDuplicateElementKey` 오류. `storage.py`가 중복을 걸러내지 않는다.
6. [낮음] `escape_md()`가 URL 자동 링크를 막지 못해 이름 속 URL이 링크가 된다. 체크박스 숨김 라벨(`f"{item['name']} 구매 완료"`)은 이스케이프하지 않는다.
7. [낮음] 손상된 `data.json`은 백업 없이 다음 저장 때 덮어써진다. 범위 밖 수량/50자 초과 이름 데이터는 수정 시 경고 없이 1/50자로 바뀐다. `add_error`는 `add_item`에서만 지워져 다른 동작 후에도 남는다.
8. [낮음] `requirements.txt`가 `streamlit>=1.40`인데 이후 버전 기능(배지 마크다운, 컨테이너 key/gap, 테마 light/dark 분리)을 쓴다. 테스트한 버전은 1.58.

## 배포

Streamlit Community Cloud(GitHub 연동, 메인 파일 `app.py`). 배포 환경에서는 재시작 시 `data.json`이 초기화되고 모든 접속자가 같은 리스트를 공유한다 (PRD상 v1에서는 허용하지만, 알려진 문제 1 때문에 동시 사용 시 데이터가 사라진다). 외부 DB 접속 정보는 `st.secrets`로 읽는다.
