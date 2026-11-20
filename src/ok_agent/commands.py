from typing import NamedTuple

from ok_agent.config import Config
from ok_agent.session import Session, refresh_models
from ok_agent.utils import display_text


class CommandResult(NamedTuple):
    invoke_agent: bool
    query: str | None = None


def handle_model_command(session: Session, query: str, config: Config):
    if session.models is None and not refresh_models(
        session, config.api_base_url, config.api_key
    ):
        return

    selected_model = query.removeprefix('/model').strip()

    if selected_model == '':
        display_text('Please pass the model id')
        return

    if selected_model == session.model:
        return

    if not session.models or selected_model not in session.models:
        display_text(f"model '{selected_model}' not found", 'ERROR')
        return

    session.model = selected_model
    display_text(f'Selected model: {selected_model}')


def handle_commands(
    query: str,
    session: Session,
    config: Config,
) -> CommandResult:
    if query.startswith('/model'):
        handle_model_command(session, query, config)

    elif query.startswith('/refresh-models'):
        if refresh_models(session, config.api_base_url, config.api_key):
            display_text('Refreshed the model list')

    elif query == '/continue':
        if not session.messages:
            display_text('History empty', style='WARNING')
            return CommandResult(False)

        previous_message = session.messages[-1]
        if previous_message['role'] in ['tool', 'user']:
            return CommandResult(True)

        return CommandResult(True, 'continue')
    else:
        return CommandResult(True, query)

    return CommandResult(False)
