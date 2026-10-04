"""Transport independent function monitoring."""

from __future__ import annotations

import functools
import sys
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, TypeVar, overload

from .cards import BaseMessage, TextMessage

F = TypeVar("F", bound=Callable[..., Any])
SuccessBuilder = Callable[[str, float, Any], BaseMessage | None]
ErrorBuilder = Callable[[str, float, Exception], BaseMessage | None]
_DEFAULT = object()


class Notifier(ABC):
    """Implement ``send`` to support another webhook transport."""

    @abstractmethod
    def send(self, message: BaseMessage) -> int:
        """Send a message and return the HTTP status code."""

    def default_success_builder(self, task_name: str, duration: float, result: Any) -> BaseMessage:
        return TextMessage(f"Task Completed: {task_name} ({duration:.2f}s)")

    def default_error_builder(self, task_name: str, duration: float, error: Exception) -> BaseMessage:
        return TextMessage(f"Task Failed: {task_name} ({duration:.2f}s): {type(error).__name__}: {error}")

    def _safe_send(self, message: BaseMessage) -> None:
        try:
            self.send(message)
        except Exception as exc:
            print(f"[chat_notifier warning] Failed to send notification: {exc}", file=sys.stderr)

    @overload
    def monitor(self, func: F, /) -> F: ...

    @overload
    def monitor(
        self,
        func: None = None,
        /,
        *,
        task_name: str | None = None,
        on_success: SuccessBuilder | None | object = _DEFAULT,
        on_error: ErrorBuilder | None | object = _DEFAULT,
    ) -> Callable[[F], F]: ...

    def monitor(
        self,
        func: F | None = None,
        /,
        *,
        task_name: str | None = None,
        on_success: SuccessBuilder | None | object = _DEFAULT,
        on_error: ErrorBuilder | None | object = _DEFAULT,
    ) -> F | Callable[[F], F]:
        """Notify after a synchronous call. ``None`` disables that notification."""

        success_builder = self.default_success_builder if on_success is _DEFAULT else on_success
        error_builder = self.default_error_builder if on_error is _DEFAULT else on_error

        def decorator(wrapped: F) -> F:
            @functools.wraps(wrapped)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                name = task_name or wrapped.__name__
                started = time.perf_counter()
                try:
                    result = wrapped(*args, **kwargs)
                except Exception as exc:
                    duration = time.perf_counter() - started
                    if error_builder is not None:
                        try:
                            message = error_builder(name, duration, exc)
                            if message is not None:
                                self._safe_send(message)
                        except Exception as builder_exc:
                            print(f"[chat_notifier warning] on_error builder failed: {builder_exc}", file=sys.stderr)
                    raise

                duration = time.perf_counter() - started
                if success_builder is not None:
                    try:
                        message = success_builder(name, duration, result)
                        if message is not None:
                            self._safe_send(message)
                    except Exception as builder_exc:
                        print(f"[chat_notifier warning] on_success builder failed: {builder_exc}", file=sys.stderr)
                return result

            return wrapper  # type: ignore[return-value]

        return decorator(func) if func is not None else decorator
