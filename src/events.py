from collections import defaultdict
from typing import Callable, Any

EVENT_USER_REGISTERED = "USER_REGISTERED"
EVENT_LOGGED_IN = "LOGGED_IN"
EVENT_LOGGED_OUT = "LOGGED_OUT"
EVENT_TOKEN_REFRESHED = "TOKEN_REFRESHED"
EVENT_LOGIN_FAILED = "LOGIN_FAILED"

class EventEmitter:
    def __init__(self):
        self._listeners = defaultdict(list)

    def on(self, event_name: str, listener: Callable[..., Any]):
        self._listeners[event_name].append(listener)

    def emit(self, event_name: str, **data):
        for listener in self._listeners[event_name]:
            try:
                listener(**data)
            except Exception as error:
                print(f"Event listener error [{event_name}]: {error}")


event_emitter = EventEmitter()