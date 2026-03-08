"""Evaluate simple step conditions for workflow engine.

Supports:
- steps.{name}.exit_code, steps.{name}.output, steps.{name}.status
- Operators: ==, !=, >, <, >=, <=
- contains() for substring checks
- Boolean literals: true, false
- Logical: and, or
"""

import re


def evaluate(condition: str, step_results: dict) -> bool:
    """Evaluate a condition string against collected step results.

    step_results: {step_name: {"exit_code": int, "output": str, "status": str}}
    """
    if not condition or not condition.strip():
        return True

    condition = condition.strip()

    # Handle 'and' / 'or' (split on top-level only)
    # Simple approach: split on ' and ' / ' or ' outside parens
    or_parts = _split_logical(condition, " or ")
    if len(or_parts) > 1:
        return any(evaluate(p, step_results) for p in or_parts)

    and_parts = _split_logical(condition, " and ")
    if len(and_parts) > 1:
        return all(evaluate(p, step_results) for p in and_parts)

    # Handle contains()
    m = re.match(r'contains\(\s*(.+?)\s*,\s*["\'](.+?)["\']\s*\)', condition)
    if m:
        val = str(_resolve(m.group(1).strip(), step_results))
        substring = m.group(2)
        return substring in val

    # Handle not contains
    m = re.match(r'not\s+contains\(\s*(.+?)\s*,\s*["\'](.+?)["\']\s*\)', condition)
    if m:
        val = str(_resolve(m.group(1).strip(), step_results))
        substring = m.group(2)
        return substring not in val

    # Handle comparison operators
    for op in ("!=", ">=", "<=", "==", ">", "<"):
        parts = condition.split(op, 1)
        if len(parts) == 2:
            left = _resolve(parts[0].strip(), step_results)
            right = _resolve(parts[1].strip(), step_results)
            return _compare(left, right, op)

    # Bare boolean
    resolved = _resolve(condition, step_results)
    return bool(resolved)


def _resolve(token: str, step_results: dict):
    """Resolve a token to its value."""
    # Boolean literals
    if token.lower() == "true":
        return True
    if token.lower() == "false":
        return False
    if token.lower() == "null" or token.lower() == "none":
        return None

    # Quoted string
    if (token.startswith('"') and token.endswith('"')) or \
       (token.startswith("'") and token.endswith("'")):
        return token[1:-1]

    # Number
    try:
        if "." in token:
            return float(token)
        return int(token)
    except ValueError:
        pass

    # Step reference: steps.{name}.{field}
    m = re.match(r'steps\.(.+?)\.(\w+)', token)
    if m:
        step_name = m.group(1)
        field = m.group(2)
        step = step_results.get(step_name, {})
        return step.get(field)

    return token


def _compare(left, right, op: str) -> bool:
    """Compare two values with the given operator."""
    # Coerce types for comparison
    if isinstance(left, str) and isinstance(right, (int, float)):
        try:
            left = type(right)(left)
        except (ValueError, TypeError):
            pass
    elif isinstance(right, str) and isinstance(left, (int, float)):
        try:
            right = type(left)(right)
        except (ValueError, TypeError):
            pass

    try:
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
        if op == ">":
            return left > right
        if op == "<":
            return left < right
        if op == ">=":
            return left >= right
        if op == "<=":
            return left <= right
    except TypeError:
        return False
    return False


def _split_logical(condition: str, operator: str) -> list[str]:
    """Split condition on a logical operator, respecting parentheses."""
    parts = []
    depth = 0
    current = ""
    i = 0
    while i < len(condition):
        if condition[i] == "(":
            depth += 1
            current += condition[i]
            i += 1
        elif condition[i] == ")":
            depth -= 1
            current += condition[i]
            i += 1
        elif depth == 0 and condition[i:i + len(operator)].lower() == operator:
            parts.append(current.strip())
            current = ""
            i += len(operator)
        else:
            current += condition[i]
            i += 1
    if current.strip():
        parts.append(current.strip())
    return parts
