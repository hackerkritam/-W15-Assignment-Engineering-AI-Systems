import ast
import operator
from datetime import datetime, timezone


_ALLOWED = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}


def calculate(expression: str) -> str:
    tree = ast.parse(expression, mode="eval")

    def evaluate(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED:
            return _ALLOWED[type(node.op)](evaluate(node.left), evaluate(node.right))
        raise ValueError("Only numeric arithmetic is supported")

    return str(evaluate(tree.body))


def current_time() -> str:
    return datetime.now(timezone.utc).isoformat()


TOOLS = {
    "calculate": calculate,
    "current_time": current_time,
}
