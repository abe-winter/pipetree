import enum, ast, inspect
import pytest
from rtan.rtan import ast_returns, expr_type, LambdaParseError

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

LAMBDA = lambda x: 121
FUNC_DICT_BAD = {Case.a: lambda x: 122, Case.b: lambda x: 123}
FUNC_DICT_GOOD = {
    Case.a: lambda x: 122,
    Case.b: lambda x: 123,
}

def test_ast_returns():
    rets = list(ast_returns(returner))
    assert len(rets) == 3
    assert {ret.value for ret in rets} == {1, 2, 3}
    assert len(list(ast_returns(enum_returner))) == 1
    assert len(list(ast_returns(tuple_returner))) == 2

def test_expr_type():
    for ret in ast_returns(returner):
        assert expr_type(ret, globals()) is int
    assert [expr_type(ret, globals()) for ret in ast_returns(enum_returner)] == [Case.a]
    assert [expr_type(ret, globals()) for ret in ast_returns(null_returner)] == [None]

    params = inspect.signature(tuple_returner).parameters
    for ret in ast_returns(tuple_returner):
        sig = expr_type(ret, globals(), params)
        assert isinstance(sig, tuple) and len(sig) == 2
        assert tuple(map(type, sig)) == (Case, inspect.Parameter)

def test_lambda():
    print(list(ast_returns(LAMBDA)))
    assert isinstance(list(ast_returns(LAMBDA))[0], ast.Constant)
    with pytest.raises(LambdaParseError):
        list(ast_returns(FUNC_DICT_BAD[Case.b]))
    assert [expr_type(ret, globals()) for ret in ast_returns(FUNC_DICT_GOOD[Case.b])] == [int]
