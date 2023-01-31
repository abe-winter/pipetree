import inspect, ast, textwrap
from typing import Iterable

def ast_returns(fn: callable) -> Iterable[ast.Return]:
    "get ast.Returns for function"
    # todo: add option to filter to direct returns, i.e. ignore like lambda in filter(), or other subdefs
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
    return filter(lambda node: isinstance(node, ast.Return), ast.walk(tree))

class UnhandledType(NotImplementedError):
    "we don't know how to process this ast node or the thing inside it"

def expr_type(expr: ast.AST, globals_: dict, params: dict | None = None):
    """Convert an ast expr (or stmt I guess, return is not an expr) to a semi-defined type signature.
    Careful: this is wrong in a bunch of cases, and mainly exists to find enums.
    """
    match expr:
        case int() | None: return type(expr)
        case ast.Attribute():
            if isinstance(expr.value, ast.Name):
                return getattr(globals_[expr.value.id], expr.attr)
            raise UnhandledType(ast.unparse(expr.value), expr.value, 'in left side of ast.Attribute', ast.unparse(expr), expr)
        case ast.Name(name):
            # note: this doesn't understand scope or locals, and so is wrong in a bunch of cases
            if params and (param := params.get(name)):
                return param
            if name in globals_:
                # warning: this is wrong; needs to check locals first
                return globals_[name]
            return expr
        case ast.Tuple():
            return tuple(expr_type(elt, globals_, params) for elt in expr.elts)
        case ast.Constant(child) | ast.Return(child):
            # recursive case
            return expr_type(child, globals_, params)
        case _:
            unparsed = 'CANT_UNPARSE'
            try:
                unparsed = ast.unparse(expr)
            except:
                pass
            raise UnhandledType(unparsed, expr)
