from typing import NamedTuple


class PartialJsonResult(NamedTuple):
    json: str
    is_complete: bool


def rescue_partial_json(string: str) -> PartialJsonResult:
    """Scans through the JSON string and adds the missing closing delimiters.

    Args:
        string: incomplete JSON string.

    Returns:
        A PartialJsonResult with the repaired JSON string and a flag indicating
        whether the input was structurally complete. For mismatched delimiters,
        returns the original string and False.
    """
    BRACES_OPEN = '{'
    BRACES_CLOSE = '}'
    BRACKET_OPEN = '['
    BRACKET_CLOSE = ']'
    QUOTE = '"'
    BACKSLASH = '\\'

    closing_delimiters: list[str] = []
    escape_next = False
    in_string = False

    for char in string:
        if escape_next:
            escape_next = False
            continue

        if char == BACKSLASH:
            escape_next = True
            continue

        if char == QUOTE:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == BRACES_OPEN:
            closing_delimiters.append(BRACES_CLOSE)
        elif char == BRACKET_OPEN:
            closing_delimiters.append(BRACKET_CLOSE)
        elif char == BRACES_CLOSE:
            if not closing_delimiters or closing_delimiters[-1] != BRACES_CLOSE:
                return PartialJsonResult(string, is_complete=False)
            closing_delimiters.pop()
        elif char == BRACKET_CLOSE:
            if not closing_delimiters or closing_delimiters[-1] != BRACKET_CLOSE:
                return PartialJsonResult(string, is_complete=False)
            closing_delimiters.pop()

    if in_string:
        closing_delimiters.append(QUOTE)

    if not closing_delimiters:
        return PartialJsonResult(string, is_complete=True)

    return PartialJsonResult(
        string + ''.join(reversed(closing_delimiters)), is_complete=False
    )
