import json
import os
from dataclasses import dataclass
from logging import getLogger
from pathlib import Path

from ok_agent.validator import ObjectSchema
from ok_agent.validator import validate_object as validate_config
from ok_agent.validator.validator import ValidationError

logger = getLogger(__name__)

CONFIG_SCHEMA: ObjectSchema = {
    "type": "object",
    "properties": {
        "api_base_url": {"type": "string"},
        "api_key": {"type": "string"},
        "history_length": {"type": "integer"},
        "preserve_reasoning": {"type": "boolean"},
        "model": {"type": "string"},
        "prompt_text": {"type": "string"},
    },
    "required": ["api_base_url"],
    "additionalProperties": False,
}


@dataclass
class Config:
    api_base_url: str
    api_key: str = ""
    preserve_reasoning: bool = False
    history_length: int = 1000
    model: str | None = None
    prompt_text: str = "> "


def get_config_dir() -> Path:
    xdg_config_path = os.getenv("XDG_CONFIG_HOME")

    if xdg_config_path:
        return Path(xdg_config_path) / "ok-agent"
    else:
        return Path.home() / ".config" / "ok-agent"


class ConfigError(ValidationError):
    def __init__(self, message: str, path: str):
        self.path = path
        super().__init__(message)


def load_config() -> dict:
    """Loads config file config.json and validates it.

    Returns:
        Validated configuration dict

    Raises:
        ConfigError: if schema validation fails
    """
    config_dir = get_config_dir()
    config_file = config_dir / "config.json"

    logger.debug(config_file)

    try:
        with open(config_file, "rb") as f:
            config = json.load(f)
            validate_config(config, CONFIG_SCHEMA)
            return config
    except ValidationError as e:
        raise ConfigError(message=e.message, path=str(config_file.resolve()))
    except json.JSONDecodeError as e:
        raise ConfigError(
            message=str(*e.args),
            path=str(config_file.resolve()),
        )
    except OSError as e:
        raise ConfigError(
            message=f"Failed to read config '{config_file}' {type(e).__name__} {e}",
            path=str(config_file.resolve()),
        )


_config_cache: Config | None = None


def get_config() -> Config:
    """Returns validated configuration.

    Raises:
        ConfigError: if config validation fails
    """
    global _config_cache
    if _config_cache:
        return _config_cache

    config = load_config()
    _config_cache = Config(**config)

    return _config_cache
