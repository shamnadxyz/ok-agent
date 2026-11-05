import json
import urllib.error
import urllib.request
from functools import lru_cache
from logging import getLogger
from typing import Literal

from ok_agent.config import get_config
from ok_agent.utils import display_text

logger = getLogger(__name__)

type Endpoint = Literal['/models', '/chat/completions']
type Method = Literal['GET', 'POST']


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


@lru_cache(maxsize=1)
def _fetch_models() -> list[str]:
    config = get_config()

    request = build_request(
        api_base_url=config.api_base_url,
        api_key=config.api_key,
        endpoint='/models',
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        data = json.loads(response.read().decode('utf-8'))

        logger.debug(f'models: {data}')

        if 'data' not in data:
            raise KeyError('data not found')

        return [entry['id'] for entry in data['data'] if 'id' in entry]


def get_models() -> list[str]:
    try:
        return _fetch_models()

    except TypeError as e:
        logger.error(e)
    except urllib.error.HTTPError as e:
        message = e.reason
        error_message = get_response_error_message(e)

        if error_message is not None:
            message = error_message

        logger.exception(message)
        display_text(f'\n{message}', 'ERROR')

    except urllib.error.URLError as e:
        logger.exception(f'{e.reason}')
    except json.JSONDecodeError:
        logger.exception('JSON decode error')
    except UnicodeDecodeError:
        logger.exception('Unicode decode error')
    except TimeoutError:
        pass

    return []
