import json
import urllib.error
import urllib.request
from logging import getLogger
from typing import Literal

logger = getLogger(__name__)

type Endpoint = Literal['/models', '/chat/completions']
type Method = Literal['GET', 'POST']


class ModelFetchError(Exception):
    """Raised when retrieving model list fails."""


def get_response_error_message(response: urllib.error.HTTPError) -> str:
    try:
        json_data = response.read().decode('utf-8')
        data = json.loads(json_data)

        return data.get('error', {}).get('message') or response.reason

    except UnicodeDecodeError as e:
        logger.exception(e.reason)
    except json.JSONDecodeError:
        logger.exception('JSON decode error')

    return response.reason


def build_request(
    api_base_url: str,
    endpoint: Endpoint,
    api_key: str,
    data: bytes | None = None,
    method: Method = 'GET',
) -> urllib.request.Request:
    url = f'{api_base_url}{endpoint}'

    request = urllib.request.Request(url, data=data, method=method)

    if api_key:
        request.add_header('Authorization', f'Bearer {api_key}')

    return request


def get_models(api_base_url: str, api_key: str) -> list[str]:
    try:
        request = build_request(
            api_base_url=api_base_url,
            api_key=api_key,
            endpoint='/models',
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read())

            logger.debug(f'models: {data}')

            return [entry['id'] for entry in data['data'] if 'id' in entry]

    except urllib.error.HTTPError as e:
        raise ModelFetchError(
            f'Request failed (HTTP {e.code}): {get_response_error_message(e)}'
        ) from e
    except TimeoutError as e:
        raise ModelFetchError('Model request timed out') from e
    except urllib.error.URLError as e:
        raise ModelFetchError(str(e)) from e
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ModelFetchError('Server returned invalid JSON') from e
    except (KeyError, TypeError) as e:
        raise ModelFetchError('Server returned unexpected data') from e
