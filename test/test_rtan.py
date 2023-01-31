import enum, ast, inspect
from rtan.rtan import ast_returns, expr_type

def returner(x):
    "I return ints"
    if x: return 1
    else: return 2
    return 3 # gets ignored

class Case(enum.Enum):
    a = 1
    b = 2

def enum_returner():
    return Case.a

def tuple_returner(x):
    if x:
        return (Case.a, x)
    else:
        return (Case.b, x)

def null_returner():
    return None

def test_ast_returns():
    rets = list(ast_returns(returner))
    assert len(rets) == 3
    assert {ret.value.value for ret in rets} == {1, 2, 3}
    assert len(list(ast_returns(enum_returner))) == 1
    assert len(list(ast_returns(tuple_returner))) == 2

def test_expr_type():
    for ret in ast_returns(returner):
        assert expr_type(ret, globals()) is int
    assert [expr_type(ret, globals()) for ret in ast_returns(enum_returner)] == [Case.a]
    assert [expr_type(ret, globals()) for ret in ast_returns(null_returner)] == [type(None)]

    params = inspect.signature(tuple_returner).parameters
    for ret in ast_returns(tuple_returner):
        sig = expr_type(ret, globals(), params)
        assert isinstance(sig, tuple) and len(sig) == 2
        assert tuple(map(type, sig)) == (Case, inspect.Parameter)
