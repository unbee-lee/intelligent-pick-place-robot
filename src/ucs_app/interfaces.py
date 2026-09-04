"""Replaceable interfaces at the UCS decision and controller seams."""

from dataclasses import dataclass
from typing import AsyncIterator, Literal, Mapping, Protocol


class DecisionProvider(Protocol):
    """Interpret one Arrangement request as a structured decision payload."""

    async def decide(self, arrangement_request: str) -> Mapping[str, object]:
        """Return one payload accepted by the UCS decision contract."""


@dataclass(frozen=True)
class ControllerUpdate:
    """One public message emitted while an SC attempts a command."""

    message_type: Literal["status", "result"]
    payload: Mapping[str, object]


class StackerController(Protocol):
    """Attempt a validated command and stream correlated public messages."""

    def execute(
        self,
        command: Mapping[str, object],
    ) -> AsyncIterator[ControllerUpdate]:
        """Yield status messages followed by one terminal result message."""
