import inspect, ast, textwrap, warnings
from typing import Iterable

class LambdaParseError(Exception):
    "case we can't parse"

def ast_returns(fn: callable) -> Iterable[ast.Return]:
    "get ast.Returns for function"
    # todo: add option to filter to direct returns, i.e. ignore like lambda in filter(), or other subdefs
    source = textwrap.dedent(inspect.getsource(fn))
    if fn.__name__ == '<lambda>':
        # todo: this may choke on cases where lambdas nest
        # todo: can I use col_offset to match the function?
        try:
            tree = ast.parse(source)
        except SyntaxError:
            warnings.warn(f"trying to recover a bad parse for {source}, but this is brittle and slightly dangerous")
            tree = ast.parse(source[source.index('lambda'):])
        lambdas = [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)]
        if len(lambdas) != 1:
            raise LambdaParseError(f"we can't parse multiple lambdas on a single line -- please fix {source}")
        return [lambdas[0].body]
    tree = ast.parse(source)
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
