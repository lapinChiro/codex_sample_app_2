import streamlit as st
import requests
from typing import Callable, Any, Dict, List
from database import (
    init_db,
    authenticate_user,
    create_user,
    list_memos,
    create_memo,
    get_memo,
    update_memo,
    delete_memo,
    search_memos,
    build_memo_tree,
    list_children,
)

init_db()

# session state helpers
if 'page' not in st.session_state:
    st.session_state.page = 'login'

if 'user' not in st.session_state:
    st.session_state.user = None

if 'offline' not in st.session_state:
    st.session_state.offline = False


def check_online() -> None:
    try:
        requests.get('https://www.google.com', timeout=3)
        st.session_state.offline = False
    except Exception:
        st.session_state.offline = True


def goto(page: str) -> None:
    st.session_state.page = page


def require_login(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if not st.session_state.user:
            goto('login')
            st.warning('Please log in.')
            return
        return func(*args, **kwargs)
    return wrapper


def login_page() -> None:
    st.title('Login')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        user = authenticate_user(email, password)
        if user:
            st.session_state.user = dict(user)
            goto('memo_list')
        else:
            st.error('Login failed')
    if st.button('Register'):
        goto('register')


def register_page() -> None:
    st.title('Register')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Create account'):
        if create_user(email, password):
            st.success('Account created')
            goto('login')
        else:
            st.error('Email already registered')
    if st.button('Back to login'):
        goto('login')


@require_login
def memo_list_page() -> None:
    st.title('Your memos')
    search_kw = st.text_input('Search')
    if st.button('Search') and search_kw:
        st.session_state.search_kw = search_kw
        goto('search_result')
        st.stop()
    if st.button('New memo'):
        st.session_state.current_memo = None
        goto('memo_detail')
        st.stop()
    memos = build_memo_tree(st.session_state.user['id'])

    def render_tree(nodes: List[Dict[str, Any]], level: int = 0) -> None:
        for node in nodes:
            label = ' ' * (level * 2) + node['title']
            if st.button(label, key=f"memo_{node['id']}"):
                st.session_state.current_memo = node['id']
                goto('memo_detail')
                st.stop()
            if node['children']:
                render_tree(node['children'], level + 1)

    render_tree(memos)
    if st.button('Logout'):
        st.session_state.user = None
        goto('login')


@require_login
def memo_detail_page() -> None:
    memo_id = st.session_state.get('current_memo')
    memo = get_memo(memo_id) if memo_id else None
    title = st.text_input('Title', value=memo['title'] if memo else '')
    body = st.text_area('Body', value=memo['body'] if memo else '', height=300)
    all_memos = list_memos(st.session_state.user['id'])
    parent_options = {0: 'None', **{m['id']: m['title']
                                    for m in all_memos if not memo or m['id'] != memo['id']}}
    parent_keys = list(parent_options.keys())
    parent_index = parent_keys.index(
        memo['parent_id']) if memo and memo['parent_id'] in parent_keys else 0
    parent_id = st.selectbox('Parent memo', parent_keys,
                             index=parent_index, format_func=lambda x: parent_options[x])
    if st.button('Save'):
        if memo:
            update_memo(memo['id'], title, body, parent_id or None)
            st.success('Updated')
        else:
            new_id = create_memo(
                st.session_state.user['id'], title, body, parent_id or None)
            st.session_state.current_memo = new_id
            st.success('Created')
    if memo:
        children = list_children(memo['id'])
        if children:
            st.subheader('Child memos')
            for child in children:
                if st.button(child['title'], key=f"child_{child['id']}"):
                    st.session_state.current_memo = child['id']
                    goto('memo_detail')
                    st.stop()
    if memo and st.button('Delete'):
        delete_memo(memo['id'])
        goto('memo_list')
        st.stop()
    if st.button('Back'):
        goto('memo_list')


@require_login
def search_result_page() -> None:
    kw = st.session_state.get('search_kw', '')
    st.title(f'Search results for "{kw}"')
    results = search_memos(st.session_state.user['id'], kw)
    for memo in results:
        if st.button(memo['title'], key=f"search_{memo['id']}"):
            st.session_state.current_memo = memo['id']
            goto('memo_detail')
            st.stop()
    if st.button('Back'):
        goto('memo_list')


def offline_notice_page() -> None:
    st.title('Offline')
    st.write('You appear to be offline. Changes will be saved locally.')
    if st.button('Retry connection'):
        check_online()
        if not st.session_state.offline:
            goto('memo_list')
            st.rerun()
    if st.button('Back'):
        goto('memo_list')


PAGES: Dict[str, Callable[[], None]] = {
    'login': login_page,
    'register': register_page,
    'memo_list': memo_list_page,
    'memo_detail': memo_detail_page,
    'search_result': search_result_page,
    'offline_notice': offline_notice_page,
}

check_online()
if st.session_state.offline and st.session_state.page != 'offline_notice':
    goto('offline_notice')

page = st.session_state.page
PAGES.get(page, login_page)()
