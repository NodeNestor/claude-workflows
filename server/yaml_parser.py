"""Minimal YAML subset parser — pure stdlib, no dependencies.

Handles only what workflow files need:
- Key-value mappings (indentation-based nesting)
- Sequences (- item)
- Strings (quoted and unquoted), numbers, booleans
- Comments (#)
"""


def parse_yaml(text: str):
    """Parse a YAML string into a Python dict/list structure."""
    lines = _preprocess(text)
    if not lines:
        return {}
    result, _ = _parse_block(lines, 0, 0)
    return result


def _preprocess(text: str) -> list[tuple[int, str]]:
    """Strip comments, blank lines. Return list of (indent, content)."""
    out = []
    for raw_line in text.split("\n"):
        # Strip inline comments (but not inside quotes)
        line = _strip_comment(raw_line)
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip())
        out.append((indent, stripped))
    return out


def _strip_comment(line: str) -> str:
    """Remove # comments that aren't inside quotes."""
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line


def _parse_value(val: str):
    """Parse a scalar value string into Python type."""
    if not val:
        return ""
    # Quoted strings
    if (val.startswith('"') and val.endswith('"')) or \
       (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    # Booleans
    low = val.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low == "null" or low == "~":
        return None
    # Numbers
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        pass
    return val


def _parse_block(lines: list[tuple[int, str]], start: int, min_indent: int):
    """Parse a block of YAML at a given indentation level.
    Returns (parsed_object, next_line_index)."""
    if start >= len(lines):
        return {}, start

    _, first_content = lines[start]

    # Detect if this block is a sequence or mapping
    if first_content.startswith("- ") or first_content == "-":
        return _parse_sequence(lines, start, min_indent)
    else:
        return _parse_mapping(lines, start, min_indent)


def _parse_mapping(lines: list[tuple[int, str]], start: int, min_indent: int):
    """Parse a YAML mapping (key: value pairs)."""
    result = {}
    i = start
    while i < len(lines):
        indent, content = lines[i]
        if indent < min_indent:
            break

        # Must be a key: value line
        colon_pos = _find_colon(content)
        if colon_pos == -1:
            # Not a mapping entry — might be end of this block
            break

        key = content[:colon_pos].strip()
        val_str = content[colon_pos + 1:].strip()

        if val_str:
            # Inline value — could be a simple scalar or inline flow
            if val_str.startswith("["):
                result[key] = _parse_inline_list(val_str)
            elif val_str.startswith("{"):
                result[key] = _parse_inline_dict(val_str)
            else:
                result[key] = _parse_value(val_str)
            i += 1
        else:
            # Value is a nested block on following lines
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                child_indent = lines[i + 1][0]
                child, i = _parse_block(lines, i + 1, child_indent)
                result[key] = child
            else:
                result[key] = None
                i += 1

    return result, i


def _parse_sequence(lines: list[tuple[int, str]], start: int, min_indent: int):
    """Parse a YAML sequence (- items)."""
    result = []
    i = start
    while i < len(lines):
        indent, content = lines[i]
        if indent < min_indent:
            break
        if not (content.startswith("- ") or content == "-"):
            break

        item_str = content[2:].strip() if content.startswith("- ") else ""

        if not item_str:
            # Nested block under this sequence item
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                child_indent = lines[i + 1][0]
                child, i = _parse_block(lines, i + 1, child_indent)
                result.append(child)
            else:
                result.append(None)
                i += 1
        elif ":" in item_str and not item_str.startswith('"'):
            # Inline mapping start: "- name: foo"
            # Reconstruct as a mapping block
            colon_pos = _find_colon(item_str)
            if colon_pos != -1:
                key = item_str[:colon_pos].strip()
                val_str = item_str[colon_pos + 1:].strip()
                entry = {}
                if val_str:
                    entry[key] = _parse_value(val_str)
                else:
                    entry[key] = None

                # Check for continuation keys at deeper indent
                item_indent = indent + 2  # the "- " shifts content by 2
                i += 1
                while i < len(lines):
                    next_indent, next_content = lines[i]
                    if next_indent < item_indent:
                        break
                    if next_content.startswith("- "):
                        break
                    nc = _find_colon(next_content)
                    if nc == -1:
                        break
                    nk = next_content[:nc].strip()
                    nv = next_content[nc + 1:].strip()
                    if nv:
                        if nv.startswith("["):
                            entry[nk] = _parse_inline_list(nv)
                        elif nv.startswith("{"):
                            entry[nk] = _parse_inline_dict(nv)
                        else:
                            entry[nk] = _parse_value(nv)
                    else:
                        if i + 1 < len(lines) and lines[i + 1][0] > next_indent:
                            child_indent = lines[i + 1][0]
                            child, i = _parse_block(lines, i + 1, child_indent)
                            entry[nk] = child
                            continue
                        else:
                            entry[nk] = None
                    i += 1
                result.append(entry)
            else:
                result.append(_parse_value(item_str))
                i += 1
        else:
            result.append(_parse_value(item_str))
            i += 1

    return result, i


def _find_colon(s: str) -> int:
    """Find the first colon that acts as a key-value separator (not inside quotes)."""
    in_single = False
    in_double = False
    for i, ch in enumerate(s):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            # Must be followed by space, end-of-string, or newline
            if i + 1 >= len(s) or s[i + 1] == " ":
                return i
    return -1


def _parse_inline_list(s: str) -> list:
    """Parse a flow-style list like [a, b, c]."""
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    if not s:
        return []
    parts = _split_flow(s)
    return [_parse_value(p.strip()) for p in parts]


def _parse_inline_dict(s: str) -> dict:
    """Parse a flow-style dict like {a: 1, b: 2}."""
    s = s.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1].strip()
    if not s:
        return {}
    result = {}
    parts = _split_flow(s)
    for part in parts:
        cp = _find_colon(part.strip())
        if cp != -1:
            k = part[:cp].strip()
            v = part[cp + 1:].strip()
            result[k] = _parse_value(v)
    return result


def _split_flow(s: str) -> list[str]:
    """Split a flow-style comma-separated string, respecting nesting."""
    parts = []
    depth = 0
    current = []
    in_single = False
    in_double = False
    for ch in s:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif not in_single and not in_double:
            if ch in ("[", "{"):
                depth += 1
            elif ch in ("]", "}"):
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(ch)
    if current:
        parts.append("".join(current))
    return parts
