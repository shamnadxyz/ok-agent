import json
import urllib.error
import urllib.request
from logging import getLogger
from typing import Literal

from ok_agent.config import get_config

logger = getLogger(__name__)

type Endpoint = Literal["/models", "/chat/completions"]
type Method = Literal["GET", "POST"]


def get_response_error_message(response: urllib.error.HTTPError) -> str:
    try:
        json_data = response.read().decode("utf-8")
        data = json.loads(json_data)

        return data.get("error", {}).get("message") or response.reason

    except UnicodeDecodeError as e:
        logger.exception(e.reason)
    except json.JSONDecodeError:
        logger.exception("JSON decode error")

    return response.reason


def build_request(
    endpoint: Endpoint,
    data: bytes | None = None,
    method: Method = "GET",
) -> urllib.request.Request:
    config = get_config()
    api_base_url = config.api_base_url
    completions_endpoint = f"{api_base_url}{endpoint}"

    request = urllib.request.Request(
        completions_endpoint, data=data, method=method
    )

    if config.api_key:
        request.add_header("Authorization", f"Bearer {config.api_key}")

    logger.debug(f"Request URL: {request.full_url}")

    return request


def get_models() -> list[str]:
    request = build_request(endpoint="/models")

    try:
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode("utf-8"))

            logger.debug(data)

            if "data" not in data:
                return []

            return [entry["id"] for entry in data["data"] if "id" in entry]
    except urllib.error.HTTPError as e:
        message = e.reason
        error_message = get_response_error_message(e)

        if error_message is not None:
            message = error_message

        logger.exception(message)
        print(f"\n{message}")

        return []
    except urllib.error.URLError as e:
        logger.exception(f"{e.reason}")
        return []
    except json.JSONDecodeError:
        logger.exception("JSON decode error")
        return []
    except UnicodeDecodeError:
        logger.exception("Unicode decode error")
        return []


def rescue_partial_json(string: str) -> str | None:
    """Scans through the JSON string and adds the missing closing delimiters.

    Args:
        string: incomplete JSON string.

    Returns:
        Completed JSON string or None if a closing delimiter is encountered
        without a matching opening delimiter.
    """
    BRACES_OPEN = "{"
    BRACES_CLOSE = "}"
    BRACKET_OPEN = "["
    BRACKET_CLOSE = "]"
    QUOTE = '"'
    BACKSLASH = "\\"

    open_delimiters: list[str] = []
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

        if char == BRACES_OPEN or char == BRACKET_OPEN:
            open_delimiters.append(char)
        elif char == BRACES_CLOSE:
            if not open_delimiters or open_delimiters[-1] != BRACES_OPEN:
                return None
            open_delimiters.pop()
        elif char == BRACKET_CLOSE:
            if not open_delimiters or open_delimiters[-1] != BRACKET_OPEN:
                return None
            open_delimiters.pop()

    if in_string:
        open_delimiters.append(QUOTE)

    if not open_delimiters:
        return string

    # Add the closing delimiters
    for char in reversed(open_delimiters):
        if char == BRACES_OPEN:
            string += BRACES_CLOSE
        elif char == BRACKET_OPEN:
            string += BRACKET_CLOSE
        else:
            string += QUOTE

    return string
