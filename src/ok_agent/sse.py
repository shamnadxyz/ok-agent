"""Process server-sent events (SSE)."""

from collections.abc import Generator, Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    id: str = ''
    type: str = 'message'
    data: str = ''
    reconnection_time: int | None = None


def parse_event_stream(stream: Iterable[bytes]) -> Generator[Event]:
    """Parse server-sent event stream."""
    event_type_buffer: str = ''
    data_buffer: str = ''
    previous_id: str = ''
    reconnection_time: int | None = None

    for raw in stream:
        line = raw.decode('utf-8').removesuffix('\n').removesuffix('\r')

        if line == '':
            if data_buffer == '':
                event_type_buffer = ''
                continue

            data_buffer = data_buffer.removesuffix('\n')

            event = Event(
                type=event_type_buffer or 'message',
                id=previous_id,
                data=data_buffer,
                reconnection_time=reconnection_time,
            )
            event_type_buffer = ''
            data_buffer = ''
            yield event

        # Ignore comments
        if line.startswith(':'):
            continue
        elif line:
            name, _, value = line.partition(':')
            value = value.removeprefix(' ')

            if name == 'event':
                event_type_buffer = value
            elif name == 'data':
                data_buffer += f'{value}\n'
            elif name == 'id' and '\0' not in value:
                previous_id = value
            elif name == 'retry' and value.isascii() and value.isdigit():
                reconnection_time = int(value)
            else:
                continue
