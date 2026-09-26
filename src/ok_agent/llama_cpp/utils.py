import json
import urllib.error
import urllib.request
from logging import getLogger
from typing import Literal

from ok_agent.config import get_config

logger = getLogger(__name__)

type Endpoint = Literal["/models", "/chat/completions"]
type Method = Literal["GET", "POST"]


def get_error_message(response: urllib.error.HTTPError) -> str | None:
    try:
        json_data = response.read().decode("utf-8")
        data = json.loads(json_data)

        return data.get("error", {}).get("message")

    except UnicodeDecodeError as e:
        logger.exception(e.reason)
    except json.JSONDecodeError:
        logger.exception("JSON decode error")


def build_request(
    endpoint: Endpoint,
    data: bytes | None = None,
    method: Method = "GET",
):
    config = get_config()
    api_base_url = config["api_base_url"]
    completions_endpoint = f"{api_base_url}{endpoint}"

    request = urllib.request.Request(
        completions_endpoint, data=data, method=method
    )

    api_key = config["api_key"]
    if api_key is not None:
        request.add_header("Authorization", f"Bearer {api_key}")

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
        error_message = get_error_message(e)

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
