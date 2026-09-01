"""Explicitly controlled development adapters for issue #4."""

import asyncio
from datetime import datetime, timezone
from typing import AsyncIterator, Mapping

from fastapi import FastAPI

from ucs_app.app import create_app
from ucs_app.interfaces import ControllerUpdate


class ControlledDecisionProvider:
    """Return one deterministic, contract-valid proposal for browser tests."""

    async def decide(self, arrangement_request: str) -> Mapping[str, object]:
        del arrangement_request
        return {
            "decision": "PROPOSE",
            "target_positions": {
                "E": "front_left",
                "B": "front_center",
                "H": "front_right",
            },
            "user_message": "Here is a complete Target arrangement to review.",
        }


class ControlledStackerController:
    """Emit deterministic correlated progress and simulated success."""

    def __init__(self, *, result_delay_seconds: float) -> None:
        if result_delay_seconds < 0:
            raise ValueError("result delay cannot be negative")
        self._result_delay_seconds = result_delay_seconds

    async def execute(
        self,
        command: Mapping[str, object],
    ) -> AsyncIterator[ControllerUpdate]:
        message_id = command.get("message_id")
        if not isinstance(message_id, str):
            raise RuntimeError("controlled SC received no message identifier")

        yield ControllerUpdate(
            message_type="status",
            payload={
                "schema_version": "1.0",
                "message_id": message_id,
                "status": "BUSY",
                "stage": "EXECUTING_MOVES",
                "timestamp": _utc_timestamp(),
            },
        )
        await asyncio.sleep(self._result_delay_seconds)
        yield ControllerUpdate(
            message_type="result",
            payload={
                "schema_version": "1.0",
                "message_id": message_id,
                "status": "DONE",
                "execution": {"status": "COMPLETED", "error": None},
                "verification": {
                    "status": "NOT_RUN",
                    "outcome": None,
                    "observed_positions": None,
                    "error": None,
                },
                "completed_at": _utc_timestamp(),
            },
        )


def create_controlled_app(*, result_delay_seconds: float = 0.75) -> FastAPI:
    """Build the explicitly labelled controlled-development composition."""

    return create_app(
        decision_provider=ControlledDecisionProvider(),
        stacker_controller=ControlledStackerController(
            result_delay_seconds=result_delay_seconds
        ),
        composition_label="Controlled development",
    )


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
