"""LangGraph workflow coordinating one controlled Arrangement request."""

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Dict, Literal, Optional, TypedDict, cast
from uuid import uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from ucs_app.interfaces import DecisionProvider, StackerController
from ucs_app.sessions import BrowserSession, SessionStore
from ucs_contracts import (
    parse_decision,
    validate_message,
    validate_target_positions,
)


class WorkflowState(TypedDict, total=False):
    """Checkpointed state for one Arrangement request."""

    session_id: str
    action: Literal["request", "confirm", "cancel"]
    arrangement_request: str
    decision_payload: Dict[str, object]
    target_positions: Dict[str, object]
    user_message: str
    command: Dict[str, object]


class UcsWorkflow:
    """Run the confirmation-gated UCS workflow behind a small interface."""

    def __init__(
        self,
        *,
        decision_provider: DecisionProvider,
        stacker_controller: StackerController,
        sessions: SessionStore,
    ) -> None:
        self._decision_provider = decision_provider
        self._stacker_controller = stacker_controller
        self._sessions = sessions

        builder = StateGraph(WorkflowState)
        builder.add_node("receive_request", self._receive_request)
        builder.add_node("interpret_request", self._interpret_request)
        builder.add_node("validate_proposal", self._validate_proposal)
        builder.add_node("store_current_draft", self._store_current_draft)
        builder.add_node("announce_confirmation", self._announce_confirmation)
        builder.add_node("prepare_command", self._prepare_command)
        builder.add_node("cancel_current_draft", self._cancel_current_draft)
        builder.add_node("deliver_command", self._deliver_command)

        builder.add_conditional_edges(
            START,
            self._route_action,
            {
                "request": "receive_request",
                "confirm": "prepare_command",
                "cancel": "cancel_current_draft",
            },
        )
        builder.add_edge("receive_request", "interpret_request")
        builder.add_edge("interpret_request", "validate_proposal")
        builder.add_edge("validate_proposal", "store_current_draft")
        builder.add_edge("store_current_draft", "announce_confirmation")
        builder.add_edge("announce_confirmation", END)
        builder.add_edge("prepare_command", "deliver_command")
        builder.add_edge("deliver_command", END)
        builder.add_edge("cancel_current_draft", END)

        self._graph = builder.compile(checkpointer=InMemorySaver())

    async def start(
        self,
        session: BrowserSession,
        arrangement_request: str,
    ) -> None:
        """Run a request until the graph pauses for confirmation."""

        if session.workflow_id is None:
            raise RuntimeError("session has no workflow identifier")
        initial_state: WorkflowState = {
            "session_id": session.session_id,
            "action": "request",
            "arrangement_request": arrangement_request,
        }
        await self._graph.ainvoke(
            initial_state,  # type: ignore[arg-type]  # LangGraph TypedDict stub mismatch
            config=self._config(session),
        )

    async def resume(
        self,
        session: BrowserSession,
        confirmation: Literal["confirm", "cancel"],
    ) -> None:
        """Resume the paused graph with an explicit browser decision."""

        resume_state: WorkflowState = {
            "session_id": session.session_id,
            "action": confirmation,
        }
        await self._graph.ainvoke(
            resume_state,  # type: ignore[arg-type]  # LangGraph TypedDict stub mismatch
            config=self._config(session),
        )

    def _config(self, session: BrowserSession) -> RunnableConfig:
        if session.workflow_id is None:
            raise RuntimeError("session has no workflow identifier")
        return {
            "configurable": {
                "thread_id": f"{session.session_id}:{session.workflow_id}",
            }
        }

    def _session(self, state: WorkflowState) -> BrowserSession:
        session = self._sessions.get(state.get("session_id"))
        if session is None:
            raise RuntimeError("browser session no longer exists")
        return session

    def _route_action(
        self,
        state: WorkflowState,
    ) -> Literal["request", "confirm", "cancel"]:
        return state["action"]

    async def _receive_request(self, state: WorkflowState) -> Dict[str, object]:
        session = self._session(state)
        arrangement_request = state["arrangement_request"]
        self._sessions.emit(
            session,
            kind="input",
            message="Typed Arrangement request received",
            details={"arrangement_request": arrangement_request},
        )
        return {}

    async def _interpret_request(self, state: WorkflowState) -> Dict[str, object]:
        payload = await self._decision_provider.decide(state["arrangement_request"])
        return {"decision_payload": dict(payload)}

    async def _validate_proposal(self, state: WorkflowState) -> Dict[str, object]:
        session = self._session(state)
        decision = parse_decision(state["decision_payload"])
        decision_payload = decision.model_dump(mode="json")
        if decision_payload.get("decision") != "PROPOSE":
            raise RuntimeError("controlled composition must return PROPOSE")

        raw_target = decision_payload.get("target_positions")
        if not isinstance(raw_target, Mapping):
            raise RuntimeError("PROPOSE decision has no Target arrangement")
        target = validate_target_positions(cast(Mapping[str, object], raw_target))
        target_positions = cast(
            Dict[str, object],
            target.model_dump(mode="json"),
        )
        user_message = decision_payload.get("user_message")
        if not isinstance(user_message, str):
            raise RuntimeError("PROPOSE decision has no safe user message")

        self._sessions.emit(
            session,
            kind="proposal",
            message=user_message,
            details={"target_positions": target_positions},
        )
        self._sessions.emit(
            session,
            kind="validation",
            message="Target arrangement validated",
        )
        return {
            "target_positions": target_positions,
            "user_message": user_message,
        }

    async def _store_current_draft(self, state: WorkflowState) -> Dict[str, object]:
        session = self._session(state)
        session.current_draft = dict(state["target_positions"])
        return {}

    async def _announce_confirmation(
        self,
        state: WorkflowState,
    ) -> Dict[str, object]:
        session = self._session(state)
        self._sessions.emit(
            session,
            kind="confirmation_required",
            message="Current draft is waiting for confirmation",
        )
        return {}

    async def _prepare_command(self, state: WorkflowState) -> Dict[str, object]:
        session = self._session(state)
        target = validate_target_positions(state["target_positions"])
        target_positions = cast(
            Dict[str, object],
            target.model_dump(mode="json"),
        )
        message_id = str(uuid4())
        command: Dict[str, object] = {
            "schema_version": "1.0",
            "message_id": message_id,
            "type": "ARRANGE",
            "target_positions": target_positions,
            "created_at": _utc_timestamp(),
        }
        validate_message("command", command)

        session.current_draft = None
        session.active_message_id = message_id
        session.active_target = target_positions
        self._sessions.emit(
            session,
            kind="confirmation",
            message="Confirmation received; Target arrangement revalidated",
        )
        return {"command": command}

    async def _cancel_current_draft(
        self,
        state: WorkflowState,
    ) -> Dict[str, object]:
        session = self._session(state)
        session.current_draft = None
        session.workflow_id = None
        self._sessions.emit(
            session,
            kind="cancellation",
            message="Current draft cancelled",
        )
        return {}

    async def _deliver_command(self, state: WorkflowState) -> Dict[str, object]:
        session = self._session(state)
        command = state["command"]
        message_id = command.get("message_id")
        if not isinstance(message_id, str):
            raise RuntimeError("validated command has no message identifier")

        self._sessions.emit(
            session,
            kind="command_publication",
            message="Command delivered to controlled Stacker Controller",
            details={"message_id": message_id},
        )

        terminal_result: Optional[Mapping[str, object]] = None
        async for update in self._stacker_controller.execute(command):
            validate_message(update.message_type, update.payload)
            if update.payload.get("message_id") != session.active_message_id:
                raise RuntimeError("Stacker Controller update is not correlated")

            if update.message_type == "status":
                stage = update.payload.get("stage")
                self._sessions.emit(
                    session,
                    kind="progress",
                    message="Stacker Controller is busy",
                    details={"stage": stage} if isinstance(stage, str) else {},
                )
            else:
                terminal_result = update.payload

        if terminal_result is None:
            raise RuntimeError("Stacker Controller returned no terminal result")
        self._apply_result(session, terminal_result)
        return {}

    def _apply_result(
        self,
        session: BrowserSession,
        result: Mapping[str, object],
    ) -> None:
        execution = result.get("execution")
        verification = result.get("verification")
        if not isinstance(execution, Mapping) or not isinstance(
            verification, Mapping
        ):
            raise RuntimeError("validated result is missing outcome details")

        execution_status = execution.get("status")
        verification_status = verification.get("status")
        if execution_status == "COMPLETED" and session.active_target is not None:
            session.last_successful_arrangement = dict(session.active_target)

        session.active_message_id = None
        session.active_target = None
        session.workflow_id = None
        self._sessions.emit(
            session,
            kind="result",
            message=(
                "Simulation completed the requested arrangement. "
                "Visual verification was not run."
            ),
            details={
                "execution_status": execution_status,
                "verification_status": verification_status,
                "last_successful_arrangement": session.last_successful_arrangement,
            },
        )


def _utc_timestamp() -> str:
    """Return an RFC 3339 UTC timestamp for public transport metadata."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
