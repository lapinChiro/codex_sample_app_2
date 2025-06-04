import streamlit as st
import db


def offline_banner():
    """Show online/offline status and sync button."""
    st.markdown(
        """
        <div id="offline_status"></div>
        <script>
        function updateStatus(){
            const el = document.getElementById('offline_status');
            if(!el) return;
            el.innerText = navigator.onLine ? '' : '⚠ Offline';
        }
        window.addEventListener('load', updateStatus);
        window.addEventListener('online', updateStatus);
        window.addEventListener('offline', updateStatus);
        setInterval(updateStatus, 2000);
        </script>
        """,
        unsafe_allow_html=True,
    )
    if st.button('Sync'):
        st.rerun()


def require_login():
    if 'user_id' not in st.session_state:
        st.session_state.page = 'login'
        st.stop()


def login_page():
    offline_banner()
    st.title('Login')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Login'):
        user_id = db.authenticate(email, password)
        if user_id:
            st.session_state.user_id = user_id
            st.session_state.page = 'list'
            st.rerun()
        else:
            st.error('Invalid credentials')
    if st.button('Sign up'):
        st.session_state.page = 'signup'
        st.rerun()


def signup_page():
    offline_banner()
    st.title('Sign Up')
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')
    if st.button('Register'):
        if db.create_user(email, password):
            st.success('Account created. Please log in.')
            st.session_state.page = 'login'
            st.rerun()
        else:
            st.error('Email already registered')
    if st.button('Back to login'):
        st.session_state.page = 'login'
        st.rerun()


def build_tree(memos):
    tree = {}
    for m_id, title, parent_id in memos:
        tree[m_id] = {'title': title, 'parent': parent_id, 'children': []}
    for m_id, data in tree.items():
        parent = data['parent']
        if parent and parent in tree:
            tree[parent]['children'].append(m_id)
    roots = [m_id for m_id, data in tree.items() if not data['parent']]
    return tree, roots


def render_tree(tree, node_id, depth=0):
    data = tree[node_id]
    st.write(' ' * depth * 2 + f"- [{data['title']}](?memo_id={node_id})")
    for child in data['children']:
        render_tree(tree, child, depth + 1)


def list_page():
    require_login()
    offline_banner()
    st.title('Your Memos')
    memos = db.list_memos(st.session_state.user_id)
    tree, roots = build_tree(memos)
    for root in roots:
        render_tree(tree, root)
    if st.button('New Memo'):
        memo_id = db.create_memo(st.session_state.user_id, 'New Memo')
        st.session_state.page = 'detail'
        st.session_state.memo_id = memo_id
        st.rerun()
    search = st.text_input('Search')
    if st.button('Search'):
        st.session_state.search = search
        st.session_state.page = 'search'
        st.rerun()
    if st.button('Settings'):
        st.session_state.page = 'settings'
        st.rerun()


def detail_page():
    require_login()
    offline_banner()
    memo = db.get_memo(st.session_state.memo_id)
    if not memo:
        st.error('Memo not found')
        st.session_state.page = 'list'
        st.rerun()
    memo_id, title, content, parent_id = memo
    st.title('Edit Memo')
    title_input = st.text_input('Title', value=title)
    content_input = st.text_area('Content', value=content, height=300)
    memos = db.list_memos(st.session_state.user_id)
    parent_options = ['None'] + [m[1] for m in memos if m[0] != memo_id]
    parent_map = {'None': None}
    for m in memos:
        if m[0] != memo_id:
            parent_map[m[1]] = m[0]
    current_parent_title = 'None'
    for title_, id_ in parent_map.items():
        if id_ == parent_id:
            current_parent_title = title_
            break
    parent_title = st.selectbox('Parent', parent_options, index=parent_options.index(current_parent_title))
    parent_id_new = parent_map[parent_title]

    if (
        'last_saved' not in st.session_state
        or st.session_state.last_saved.get('memo_id') != memo_id
    ):
        st.session_state.last_saved = {
            'memo_id': memo_id,
            'title': title,
            'content': content,
            'parent_id': parent_id,
        }

    changed = (
        title_input != st.session_state.last_saved['title']
        or content_input != st.session_state.last_saved['content']
        or parent_id_new != st.session_state.last_saved['parent_id']
    )
    if title_input and content_input:
        if changed:
            db.update_memo(memo_id, title_input, content_input, parent_id_new)
            st.session_state.last_saved = {
                'memo_id': memo_id,
                'title': title_input,
                'content': content_input,
                'parent_id': parent_id_new,
            }
            st.info('Auto-saved')

        if st.button('Save'):
            db.update_memo(memo_id, title_input, content_input, parent_id_new)
            st.success('Saved')
    if st.button('Delete'):
        db.delete_memo(memo_id)
        st.session_state.page = 'list'
        st.rerun()
    if st.button('Back'):
        st.session_state.page = 'list'
        st.rerun()


def search_page():
    require_login()
    offline_banner()
    query = st.session_state.get('search', '')
    st.title('Search results')
    results = db.search_memos(st.session_state.user_id, query)
    for memo_id, title in results:
        st.write(f"- [{title}](?memo_id={memo_id})")
    if st.button('Back'):
        st.session_state.page = 'list'
        st.rerun()


def settings_page():
    """Account settings with password change and logout."""
    require_login()
    offline_banner()
    st.title('Settings')
    with st.form('change_pw'):
        current = st.text_input('Current password', type='password')
        new_pw = st.text_input('New password', type='password')
        submitted = st.form_submit_button('Change Password')
        if submitted:
            if db.change_password(st.session_state.user_id, current, new_pw):
                st.success('Password updated')
            else:
                st.error('Incorrect current password')
    if st.button('Logout'):
        st.session_state.clear()
        st.session_state.page = 'login'
        st.rerun()
    if st.button('Back'):
        st.session_state.page = 'list'
        st.rerun()


def main():
    db.init_db()
    page = st.session_state.get('page', 'login')
    if 'memo_id' in st.experimental_get_query_params():
        st.session_state.memo_id = st.experimental_get_query_params()['memo_id'][0]
        page = 'detail'
    if page == 'login':
        login_page()
    elif page == 'signup':
        signup_page()
    elif page == 'list':
        list_page()
    elif page == 'detail':
        if 'memo_id' not in st.session_state:
            st.session_state.page = 'list'
            st.rerun()
        detail_page()
    elif page == 'search':
        search_page()
    elif page == 'settings':
        settings_page()


if __name__ == '__main__':
    main()

