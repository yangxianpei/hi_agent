
EVENTS= []
def add_tool_event(event) -> None:
    EVENTS.append(event)

def get_tool_event() -> None:
    if(len(EVENTS) > 0):
        event = EVENTS.pop(0)
        return [event]
    else:
        return []

def clear_tool_event() -> None:
    EVENTS.clear()
