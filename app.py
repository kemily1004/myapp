"""쇼핑 리스트 Streamlit 앱."""

import string
import uuid
from datetime import datetime

import streamlit as st

from storage import load_items, save_items

st.set_page_config(page_title="쇼핑 리스트", page_icon="🛒", layout="centered")

NAME_MAX_LEN = 50
QTY_MIN, QTY_MAX = 1, 999
FILTERS = ["전체", "남은 항목", "완료 항목"]

# 사용자 입력이 들어가지 않는 고정 CSS만 둔다. 색은 테마 변수/반투명 값을 써서 라이트·다크 모두 대응한다.
CUSTOM_CSS = """
<style>
/* 좁은 화면에서도 추가 폼과 아이템 행의 열이 세로로 쌓이지 않게 한다 */
.st-key-add_area [data-testid="stHorizontalBlock"],
.st-key-item_list [data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap;
    gap: 0.5rem;
}
.st-key-add_area [data-testid="stColumn"],
.st-key-item_list [data-testid="stColumn"] {
    min-width: 0;
}
/* 아이템 카드 */
.st-key-item_list [class*="st-key-row_"] {
    padding: 0.35rem 0.75rem;
}
.st-key-item_list [class*="st-key-row_done_"] {
    opacity: 0.6;
}
/* Streamlit 기본 마크다운 여백(p 아래 1rem + 컨테이너 -1rem)을 없애 세로 가운데 정렬을 맞춘다 */
.st-key-item_list [data-testid="stMarkdownContainer"] {
    margin-bottom: 0;
}
.st-key-item_list [data-testid="stMarkdownContainer"] p {
    margin: 0;
    overflow-wrap: anywhere;
}
/* 수정/삭제 아이콘 버튼: 손가락으로 누르기 쉬운 크기 */
.st-key-item_list button {
    min-height: 2.5rem;
    min-width: 2.5rem;
    padding: 0;
}
/* 빈 리스트 안내 */
.st-key-empty_state {
    text-align: center;
    padding: 2rem 0;
}
/* 위험 동작 버튼 */
.st-key-clear_all button:not(:disabled),
.st-key-confirm_clear_all_btn button {
    color: #e5484d;
    border-color: #e5484d;
}
.st-key-confirm_clear_all_btn button {
    background: rgba(229, 72, 77, 0.12);
}
</style>
"""


# ---------- 상태 / 유틸 ----------

def init_state() -> None:
    """세션 상태를 초기화한다. 최초 실행 시에만 data.json을 읽는다.

    session_state["items"]는 반드시 대괄호로 접근한다.
    st.session_state.items는 dict의 .items() 메서드로 해석된다.
    """
    if "items" not in st.session_state:
        st.session_state["items"] = load_items()
    st.session_state.setdefault("editing_id", None)
    st.session_state.setdefault("add_error", None)
    st.session_state.setdefault("edit_error", None)
    st.session_state.setdefault("confirm_clear_all", False)
    st.session_state.setdefault("toast", None)


def get_items() -> list[dict]:
    return st.session_state["items"]


def set_items(items: list[dict]) -> None:
    st.session_state["items"] = items
    save_items(items)


def find_item(item_id: str) -> dict | None:
    return next((item for item in get_items() if item["id"] == item_id), None)


def validate(name: str, quantity) -> tuple[str, int, str | None]:
    """입력값을 정리하고 검증한다. (정리된 이름, 수량, 오류 메시지)를 반환한다."""
    name = (name or "").strip()
    if not name:
        return name, 0, "아이템 이름을 입력해 주세요."
    if len(name) > NAME_MAX_LEN:
        return name, 0, f"아이템 이름은 {NAME_MAX_LEN}자 이하로 입력해 주세요."
    try:
        qty = int(quantity)
    except (TypeError, ValueError):
        return name, 0, "수량은 숫자로 입력해 주세요."
    if not QTY_MIN <= qty <= QTY_MAX:
        return name, 0, f"수량은 {QTY_MIN}~{QTY_MAX} 사이로 입력해 주세요."
    return name, qty, None


def escape_md(text: str) -> str:
    """사용자 입력이 마크다운/HTML로 해석되지 않도록 모든 ASCII 문장부호를 이스케이프한다."""
    return "".join("\\" + ch if ch in string.punctuation else ch for ch in text)


def queue_toast(message: str, icon: str) -> None:
    """콜백에서 알림을 예약한다. 실제 표시는 다음 렌더링에서 한다."""
    st.session_state["toast"] = (message, icon)


# ---------- 콜백 ----------

def add_item() -> None:
    name, qty, error = validate(st.session_state["new_name"], st.session_state["new_qty"])
    st.session_state["add_error"] = error
    if error:
        return
    new_item = {
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": qty,
        "checked": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    set_items(get_items() + [new_item])
    queue_toast(f"추가했어요: {escape_md(name)}", "✅")


def toggle_item(item_id: str) -> None:
    checked = st.session_state[f"check_{item_id}"]
    set_items([{**item, "checked": checked} if item["id"] == item_id else item for item in get_items()])


def delete_item(item_id: str) -> None:
    item = find_item(item_id)
    if st.session_state["editing_id"] == item_id:
        cancel_edit()
    set_items([item for item in get_items() if item["id"] != item_id])
    if item:
        queue_toast(f"삭제했어요: {escape_md(item['name'])}", "🗑️")


def start_edit(item_id: str) -> None:
    item = find_item(item_id)
    if item is None:
        return
    st.session_state["editing_id"] = item_id
    st.session_state["edit_error"] = None
    st.session_state[f"edit_name_{item_id}"] = item["name"]
    st.session_state[f"edit_qty_{item_id}"] = item["quantity"]


def save_edit(item_id: str) -> None:
    name, qty, error = validate(
        st.session_state[f"edit_name_{item_id}"], st.session_state[f"edit_qty_{item_id}"]
    )
    st.session_state["edit_error"] = error
    if error:
        return
    set_items([{**item, "name": name, "quantity": qty} if item["id"] == item_id else item for item in get_items()])
    st.session_state["editing_id"] = None


def cancel_edit() -> None:
    st.session_state["editing_id"] = None
    st.session_state["edit_error"] = None


def clear_checked() -> None:
    if any(item["id"] == st.session_state["editing_id"] and item["checked"] for item in get_items()):
        cancel_edit()
    removed = sum(item["checked"] for item in get_items())
    set_items([item for item in get_items() if not item["checked"]])
    queue_toast(f"체크된 항목 {removed}개를 삭제했어요", "🗑️")


def request_clear_all() -> None:
    st.session_state["confirm_clear_all"] = True


def confirm_clear_all() -> None:
    cancel_edit()
    st.session_state["confirm_clear_all"] = False
    set_items([])
    queue_toast("모든 항목을 삭제했어요", "🗑️")


def cancel_clear_all() -> None:
    st.session_state["confirm_clear_all"] = False


# ---------- 화면 ----------

def render_toast() -> None:
    if st.session_state["toast"]:
        message, icon = st.session_state["toast"]
        st.toast(message, icon=icon)
        st.session_state["toast"] = None


def render_header() -> None:
    st.title("🛒 쇼핑 리스트")
    items = get_items()
    total = len(items)
    done = sum(item["checked"] for item in items)
    st.progress(done / total if total else 0.0, text=f"**{done} / {total}** 구매 완료")


def render_add_form() -> None:
    with st.container(key="add_area"):
        with st.form("add_form", clear_on_submit=True, border=False):
            name_col, qty_col, btn_col = st.columns([0.62, 0.2, 0.18], vertical_alignment="bottom")
            name_col.text_input("아이템 이름", key="new_name", max_chars=NAME_MAX_LEN, placeholder="예: 우유")
            qty_col.number_input("수량", key="new_qty", min_value=QTY_MIN, max_value=QTY_MAX, value=1, step=1)
            btn_col.form_submit_button("추가", on_click=add_item, type="primary", use_container_width=True)
        if st.session_state["add_error"]:
            st.warning(st.session_state["add_error"], icon="⚠️")


def render_view_row(item: dict) -> None:
    item_id = item["id"]
    row_key = f"row_done_{item_id}" if item["checked"] else f"row_{item_id}"
    with st.container(border=True, key=row_key):
        check_col, name_col, qty_col, edit_col, del_col = st.columns(
            [0.09, 0.55, 0.14, 0.11, 0.11], vertical_alignment="center", gap="small"
        )
        check_col.checkbox(
            f"{item['name']} 구매 완료",
            value=item["checked"],
            key=f"check_{item_id}",
            on_change=toggle_item,
            args=(item_id,),
            label_visibility="collapsed",
        )
        name = escape_md(item["name"])
        name_col.markdown(f":gray[~~{name}~~]" if item["checked"] else name)
        badge_color = "gray" if item["checked"] else "blue"
        qty_col.markdown(f":{badge_color}-badge[x{item['quantity']}]")
        edit_col.button(
            ":material/edit:", key=f"edit_{item_id}", on_click=start_edit, args=(item_id,),
            help="수정", type="tertiary",
        )
        del_col.button(
            ":material/delete:", key=f"del_{item_id}", on_click=delete_item, args=(item_id,),
            help="삭제", type="tertiary",
        )


def render_edit_row(item: dict) -> None:
    item_id = item["id"]
    with st.container(border=True, key=f"row_{item_id}"):
        name_col, qty_col, save_col, cancel_col = st.columns(
            [0.5, 0.2, 0.15, 0.15], vertical_alignment="center", gap="small"
        )
        name_col.text_input(
            "아이템 이름", key=f"edit_name_{item_id}", max_chars=NAME_MAX_LEN, label_visibility="collapsed"
        )
        qty_col.number_input(
            "수량", key=f"edit_qty_{item_id}", min_value=QTY_MIN, max_value=QTY_MAX, step=1,
            label_visibility="collapsed",
        )
        save_col.button(
            ":material/check:", key=f"save_{item_id}", on_click=save_edit, args=(item_id,),
            help="저장", type="primary",
        )
        cancel_col.button(":material/close:", key=f"cancel_{item_id}", on_click=cancel_edit, help="취소")
        if st.session_state["edit_error"]:
            st.warning(st.session_state["edit_error"], icon="⚠️")


def render_empty_state(message: str) -> None:
    with st.container(key="empty_state"):
        st.markdown("## 🧺")
        st.caption(message)


def render_item_list() -> None:
    items = get_items()
    if not items:
        render_empty_state("리스트가 비어 있어요. 살 물건을 추가해 보세요!")
        return

    selected = st.radio("필터", FILTERS, key="filter", horizontal=True, label_visibility="collapsed")
    if selected == "남은 항목":
        items = [item for item in items if not item["checked"]]
    elif selected == "완료 항목":
        items = [item for item in items if item["checked"]]

    # 미체크 항목을 위로 (sorted는 안정 정렬이라 추가 순서가 유지됨)
    items = sorted(items, key=lambda item: item["checked"])
    if not items:
        render_empty_state("해당하는 항목이 없어요.")
        return
    with st.container(key="item_list", gap="small"):
        for item in items:
            if item["id"] == st.session_state["editing_id"]:
                render_edit_row(item)
            else:
                render_view_row(item)


def render_footer() -> None:
    items = get_items()
    if not items:
        return
    st.divider()
    if st.session_state["confirm_clear_all"]:
        st.warning("정말 모든 항목을 삭제할까요? 되돌릴 수 없어요.", icon="⚠️")
        yes_col, no_col = st.columns(2)
        yes_col.button(
            "삭제", key="confirm_clear_all_btn", on_click=confirm_clear_all,
            icon=":material/delete_forever:", use_container_width=True,
        )
        no_col.button("취소", key="cancel_clear_all", on_click=cancel_clear_all, use_container_width=True)
        return

    checked_col, all_col = st.columns(2)
    checked_col.button(
        "체크된 항목 삭제",
        key="clear_checked",
        on_click=clear_checked,
        disabled=not any(item["checked"] for item in items),
        icon=":material/playlist_remove:",
        use_container_width=True,
    )
    all_col.button(
        "전체 삭제", key="clear_all", on_click=request_clear_all,
        icon=":material/delete_forever:", use_container_width=True,
    )


def main() -> None:
    init_state()
    st.html(CUSTOM_CSS)
    render_toast()
    render_header()
    render_add_form()
    render_item_list()
    render_footer()


main()
