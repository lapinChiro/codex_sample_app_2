import sys
import types
import importlib
import os

# Minimal streamlit stub
calls = {}

def fake_markdown(html, **kwargs):
    calls['markdown'] = html

st_stub = types.SimpleNamespace(
    markdown=fake_markdown,
    button=lambda label: False,
    experimental_rerun=lambda: None,
    session_state={}
)

sys.modules['streamlit'] = st_stub

# Passlib stub so importing app works
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

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app
importlib.reload(app)


def test_offline_banner_contains_script():
    app.offline_banner()
    assert 'navigator.onLine' in calls.get('markdown', '')
