import dis, inspect, ast, textwrap
from typing import Iterable, Tuple

def returns(fn):
    "get instructions of fn's bytecode, return a list of reverse iterators for each"
    instrs = list(dis.get_instructions(fn))
    return_indices = []
    for i, inst in enumerate(instrs):
        if inst.opname == 'RETURN_VALUE':
            return_indices.append(i)
    return [instrs[i::-1] for i in return_indices]

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
        case int(): return int
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
            raise UnhandledType(ast.unparse(expr), expr)
