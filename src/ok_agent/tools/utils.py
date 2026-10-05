from ok_agent.tools.types import ArgumentState, ToolDisplayState


def is_complete(name: str, state: ToolDisplayState) -> bool:
    """Returns whether the streaming of the argument is complete.

    Args:
        name: Name of the argument field.
        state: Dictionary used to track the state of streaming.
    """
    argument_states = state.get("argument_states")
    argument_state = argument_states.get(name) or {}
    return argument_state.get("is_complete") or False


def handle_argument_display(
    name: str,
    state: ToolDisplayState,
    data: dict,
    prefix: str = "",
    suffix: str = "",
):
    """Display streaming argument and track progress.

    Args:
        name: Name of the argument to track.
        prefix: String to print before argument.
        suffix: String to print after argument.
        state: State dictionary for tracking progress.
        data: Parsed arguments dictionary
    """
    if name not in data:
        return

    argument_states = state["argument_states"]
    argument_state = argument_states.get(name)

    if not argument_state:
        argument_state: ArgumentState = {"is_complete": False, "offset": 0}
        argument_states[name] = argument_state

    if argument_state["is_complete"]:
        return

    offset = argument_state["offset"]

    argument: str = data[name]
    argument_length = len(argument)

    if argument_length == 0:
        return

    if offset != 0 and offset == argument_length:
        argument_state["is_complete"] = True
        print()
        return

    slice = argument[offset:]

    print(
        f"{prefix}{slice}{suffix}",
        end="",
        flush=True,
    )

    argument_state["offset"] = argument_length
