import os
from pathlib import Path
import database

def setup_function(function):
    database.DB_PATH = Path('test.db')
    if database.DB_PATH.exists():
        os.remove(database.DB_PATH)
    database.init_db()

def teardown_function(function):
    if database.DB_PATH.exists():
        os.remove(database.DB_PATH)

def test_user_creation_and_authentication():
    assert database.create_user('user@example.com', 'pass')
    # duplicate registration should fail
    assert not database.create_user('user@example.com', 'pass')
    user = database.authenticate_user('user@example.com', 'pass')
    assert user is not None
    assert user['email'] == 'user@example.com'
    assert database.authenticate_user('user@example.com', 'wrong') is None

def test_memo_crud_and_hierarchy():
    database.create_user('user@example.com', 'pass')
    user = database.authenticate_user('user@example.com', 'pass')
    uid = user['id']
    parent = database.create_memo(uid, 'parent', 'body', None)
    child = database.create_memo(uid, 'child', 'body2', parent)
    tree = database.build_memo_tree(uid)
    assert tree and tree[0]['id'] == parent
    assert tree[0]['children'][0]['id'] == child
    children = database.list_children(parent)
    assert len(children) == 1 and children[0]['id'] == child
    database.update_memo(child, 'child updated', 'body3', parent)
    memo = database.get_memo(child)
    assert memo['title'] == 'child updated'
    database.delete_memo(child)
    assert database.get_memo(child) is None

def test_search_memos():
    database.create_user('user@example.com', 'pass')
    user = database.authenticate_user('user@example.com', 'pass')
    uid = user['id']
    database.create_memo(uid, 'Alpha memo', 'contains keyword', None)
    database.create_memo(uid, 'Other memo', 'something else', None)
    results = database.search_memos(uid, 'keyword')
    assert any(r['title'] == 'Alpha memo' for r in results)
