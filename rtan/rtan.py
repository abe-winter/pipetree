import inspect, ast, textwrap, warnings, types, logging
from typing import Iterable, Generator

logger = logging.getLogger(__name__)

class LambdaParseError(Exception):
    "case we can't parse"

def expand_ret_expr(expr: ast.AST):
    "if a return value is actually multiple return values, expand it"
    match expr:
        case ast.IfExp(_, body, orelse):
            return [*expand_ret_expr(body), *expand_ret_expr(orelse)]
    return [expr]

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
            logger.debug('about to recover from bad parse for %s', source)
            warnings.warn(f"trying to recover a bad parse, but this is brittle")
            tree = ast.parse(source[source.index('lambda'):])
        lambdas = [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)]
        if len(lambdas) != 1:
            raise LambdaParseError(f"we can't parse multiple lambdas on a single line -- please fix {source}")
        yield from expand_ret_expr(lambdas[0].body)
        return
    tree = ast.parse(source)
    for node in filter(lambda node: isinstance(node, ast.Return), ast.walk(tree)):
        yield from expand_ret_expr(node.value)

class UnhandledType(NotImplementedError):
    "we don't know how to process this ast node or the thing inside it"

def get_global(globals_: dict | types.ModuleType, key: str):
    return globals_[key] if isinstance(globals_, dict) else getattr(globals_, key)

def expr_type(expr: ast.AST, globals_: dict, params: dict | None = None):
    """Convert an ast expr (or stmt I guess, return is not an expr) to a semi-defined type signature.
    Careful: this is wrong in a bunch of cases, and mainly exists to find enums.
    """
    match expr:
        case None: return None
        case int(): return type(expr)
        case ast.Attribute():
            if isinstance(expr.value, ast.Name):
                return getattr(get_global(globals_, expr.value.id), expr.attr)
            raise UnhandledType(ast.unparse(expr.value), expr.value, 'in left side of ast.Attribute', ast.unparse(expr), expr)
        case ast.Name(name):
            # note: this doesn't understand scope or locals, and so is wrong in a bunch of cases
            if params and (param := params.get(name)):
                return param
            if name in globals_:
                # warning: this is wrong; needs to check locals first
                return get_global(globals_, name)
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

def typed_rets(fn, globals_) -> Generator:
    "helper to call ast_returns on fn then expr_type on each ret"
    params = inspect.signature(fn).parameters
    for ret in ast_returns(fn):
        yield expr_type(ret, globals_, params)
