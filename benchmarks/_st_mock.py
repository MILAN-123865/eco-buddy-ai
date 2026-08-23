"""Inject lightweight fakes for streamlit and optional heavy packages."""
import sys
import types

_INJECTED = []


def _cache_data(*args, **kwargs):
    def wrap(fn):
        if not hasattr(fn, "clear"):
            fn.clear = lambda: None
        return fn
    return wrap(args[0]) if args and callable(args[0]) else wrap


class SessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            if key == "user":
                self["user"] = {"id": 1, "email": "test@example.com"}
                return self["user"]
            raise AttributeError(f"'SessionState' object has no attribute '{key}'")
    def __setattr__(self, key, value):
        self[key] = value


class MockContextManager:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def __call__(self, *args, **kwargs):
        return self
    def __getitem__(self, item):
        return self
    def __iter__(self):
        return iter([self])


def _noop(*a, **k):
    return MockContextManager()


def _make_st():
    st = types.ModuleType("streamlit")
    st.cache_data = _cache_data
    st.cache_resource = _cache_data
    st.session_state = SessionState()

    def columns(spec, *args, **kwargs):
        if isinstance(spec, int):
            count = spec
        else:
            try:
                count = len(spec)
            except:
                count = 1
        return [MockContextManager() for _ in range(count)]

    def tabs(tabs_list, *args, **kwargs):
        try:
            count = len(tabs_list)
        except:
            count = 1
        return [MockContextManager() for _ in range(count)]

    st.columns = columns
    st.tabs = tabs

    # Standard layout elements that are context managers
    for n in ("sidebar", "container", "expander", "chat_message", "status"):
        setattr(st, n, lambda *a, **k: MockContextManager())

    # Input widgets returning values
    for n in ("text_input", "text_area"):
        setattr(st, n, lambda *a, **k: "")
    for n in ("number_input", "slider"):
        setattr(st, n, lambda *a, **k: 0.0)
    for n in ("checkbox", "toggle", "button"):
        setattr(st, n, lambda *a, **k: False)
    for n in ("multiselect",):
        setattr(st, n, lambda *a, **k: [])
    for n in ("file_uploader", "date_input", "time_input"):
        setattr(st, n, lambda *a, **k: None)

    def selectbox(label, options, *a, **k):
        try: return options[0] if options else ""
        except: return ""
    st.selectbox = selectbox
    st.radio = selectbox

    # General display methods
    for n in ("error","warning","info","success","write","title","header",
              "subheader","text","markdown","spinner","plotly_chart","metric","stop",
              "empty","divider","dataframe","table","latex","code","json","caption","toast","chat_input","progress"):
        setattr(st, n, lambda *a, **k: None)
    return st


def _make_pdfplumber():
    m = types.ModuleType("pdfplumber")
    class _PDF:
        pages = []
        def __enter__(self): return self
        def __exit__(self, *_): return False
    m.open = lambda *a, **k: _PDF()
    return m


def _make_pytesseract():
    m = types.ModuleType("pytesseract")
    m.image_to_string = lambda *a, **k: ""
    return m


def _make_reportlab():
    mods = {}
    def sub(name):
        m = types.ModuleType(name); mods[name] = m; return m
    rl  = sub("reportlab")
    pl  = sub("reportlab.platypus")
    lib = sub("reportlab.lib")
    sty = sub("reportlab.lib.styles")
    class _Doc:
        def __init__(self, *a, **k): pass
        def build(self, *a, **k): pass
    class _Para:
        def __init__(self, t, s=None, *a, **k): pass
    pl.SimpleDocTemplate = _Doc
    pl.Paragraph = _Para
    class _SS(dict):
        def __getitem__(self, k): return k
    sty.getSampleStyleSheet = _SS
    return mods


def install_streamlit_mock():
    for name, factory in [("streamlit", _make_st),
                           ("pdfplumber", _make_pdfplumber),
                           ("pytesseract", _make_pytesseract)]:
        if name not in sys.modules:
            sys.modules[name] = factory()
            _INJECTED.append(name)
    try:
        import reportlab
    except ImportError:
        for name, mod in _make_reportlab().items():
            if name not in sys.modules:
                sys.modules[name] = mod
                _INJECTED.append(name)


def remove_streamlit_mock():
    for k in list(_INJECTED):
        sys.modules.pop(k, None)
    _INJECTED.clear()
