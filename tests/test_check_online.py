import ast
import types
import sys

# Provide a minimal requests stub if the real library is unavailable
try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - environment without internet
    requests = types.SimpleNamespace(RequestException=Exception)
    sys.modules['requests'] = requests
if not hasattr(requests, 'get'):
    requests.get = lambda *a, **k: None

# Load source of app.py and extract check_online function
with open('app.py') as f:
    source = f.read()
module = ast.parse(source)
check_node = None
for node in module.body:
    if isinstance(node, ast.FunctionDef) and node.name == 'check_online':
        check_node = node
        break
assert check_node is not None
mod = ast.Module(body=[check_node], type_ignores=[])
compiled = compile(mod, filename='app.py', mode='exec')

class DummyStreamlit:
    def __init__(self):
        from types import SimpleNamespace
        self.session_state = SimpleNamespace()

dummy_st = DummyStreamlit()
namespace = {'requests': requests, 'st': dummy_st}
exec(compiled, namespace)
check_online = namespace['check_online']

def test_check_online_offline(monkeypatch):
    def raise_err(*args, **kwargs):
        raise requests.RequestException
    monkeypatch.setattr(requests, 'get', raise_err)
    check_online()
    assert dummy_st.session_state.offline is True

def test_check_online_online(monkeypatch):
    class Resp:
        status_code = 200
    monkeypatch.setattr(requests, 'get', lambda *a, **k: Resp())
    dummy_st.session_state.offline = True
    check_online()
    assert dummy_st.session_state.offline is False
