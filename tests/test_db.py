import sys
import types

# Stub passlib bcrypt
class BcryptStub:
    @staticmethod
    def hash(pw):
        return f"hash_{pw}"

    @staticmethod
    def verify(pw, hashed):
        return hashed == f"hash_{pw}"

passlib_mod = types.ModuleType('passlib')
hash_mod = types.ModuleType('passlib.hash')
hash_mod.bcrypt = BcryptStub
passlib_mod.hash = hash_mod
sys.modules.setdefault('passlib', passlib_mod)
sys.modules.setdefault('passlib.hash', hash_mod)

import os
import tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db


def setup_function(func):
    # Use a temporary database for each test
    tmp = tempfile.NamedTemporaryFile(delete=False)
    tmp.close()
    db.DB_PATH = tmp.name
    db.bcrypt = BcryptStub
    db.init_db()
    func._db_path = tmp.name


def teardown_function(func):
    os.unlink(func._db_path)


def test_create_user_and_authenticate():
    assert db.create_user('a@example.com', 'pw1')
    assert not db.create_user('a@example.com', 'pw1')  # duplicate
    user_id = db.authenticate('a@example.com', 'pw1')
    assert user_id is not None
    assert db.authenticate('a@example.com', 'bad') is None


def test_memo_crud_and_listing():
    assert db.create_user('b@example.com', 'pw')
    user_id = db.authenticate('b@example.com', 'pw')
    memo_id = db.create_memo(user_id, 'Title', 'Body')
    memo = db.get_memo(memo_id)
    assert memo[0] == memo_id
    assert memo[1] == 'Title'
    db.update_memo(memo_id, 'New', 'Body2', None)
    memo = db.get_memo(memo_id)
    assert memo[1] == 'New'
    memos = db.list_memos(user_id)
    assert len(memos) == 1
    db.delete_memo(memo_id)
    assert db.get_memo(memo_id) is None


def test_search_and_parent():
    assert db.create_user('c@example.com', 'pw')
    uid = db.authenticate('c@example.com', 'pw')
    root_id = db.create_memo(uid, 'root', 'hello world')
    child_id = db.create_memo(uid, 'child', 'body', parent_id=root_id)
    results = db.search_memos(uid, 'hello')
    assert (root_id, 'root') in results
    memo = db.get_memo(child_id)
    assert memo[3] == root_id


def test_change_password():
    assert db.create_user('d@example.com', 'old')
    uid = db.authenticate('d@example.com', 'old')
    assert db.change_password(uid, 'old', 'new')
    assert db.authenticate('d@example.com', 'new') == uid
    assert not db.change_password(uid, 'bad', 'x')
