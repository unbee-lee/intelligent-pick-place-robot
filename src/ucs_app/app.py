"""FastAPI interface for the browser-observable User Command Station."""

import asyncio
from importlib.resources import files
from typing import AsyncIterator, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, ConfigDict, field_validator

from ucs_app.interfaces import DecisionProvider, StackerController
from ucs_app.sessions import BrowserSession, SessionStore
from ucs_app.workflow import UcsWorkflow

_SESSION_COOKIE = "ucs_session"


class ArrangementRequestBody(BaseModel):
    """Typed request submitted through the browser interface."""

    model_config = ConfigDict(extra="forbid")

    text: str

    @field_validator("text")
    @classmethod
    def text_is_not_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Arrangement request cannot be empty")
        return stripped


def create_app(
    *,
    decision_provider: DecisionProvider,
    stacker_controller: StackerController,
    composition_label: str,
) -> FastAPI:
    """Build a UCS from explicit adapters at its two external seams."""

    sessions = SessionStore()
    workflow = UcsWorkflow(
        decision_provider=decision_provider,
        stacker_controller=stacker_controller,
        sessions=sessions,
    )
    application = FastAPI(title="User Command Station")

    @application.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        session = sessions.get(request.cookies.get(_SESSION_COOKIE))
        if session is None:
            session = sessions.create()

        html = (
            files("ucs_app")
            .joinpath("web/index.html")
            .read_text(encoding="utf-8")
            .replace("{{COMPOSITION_LABEL}}", composition_label)
        )
        response = HTMLResponse(html)
        response.set_cookie(
            _SESSION_COOKIE,
            session.session_id,
            httponly=True,
            samesite="lax",
        )
        return response

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "composition": composition_label}

    @application.get("/events")
    async def events(request: Request) -> StreamingResponse:
        session = _require_session(request, sessions)
        subscriber = session.subscribe()

        async def event_stream() -> AsyncIterator[str]:
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(subscriber.get(), timeout=15)
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
                        continue
                    yield event.as_sse()
            finally:
                session.unsubscribe(subscriber)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @application.post("/arrangement-requests", status_code=status.HTTP_202_ACCEPTED)
    async def submit_arrangement_request(
        body: ArrangementRequestBody,
        request: Request,
    ) -> dict[str, str]:
        session = _require_session(request, sessions)
        async with session.lock:
            if (
                session.current_draft is not None
                or session.active_command is not None
                or session.confirmation_in_progress
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Finish the Current draft or Active command first",
                )
            session.workflow_id = str(uuid4())

        try:
            await workflow.start(session, body.text)
        except Exception:
            session.workflow_id = None
            session.current_draft = None
            raise
        return {"status": "awaiting_confirmation"}

    @application.post(
        "/current-draft/{confirmation}",
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def decide_current_draft(
        confirmation: Literal["confirm", "cancel"],
        request: Request,
    ) -> dict[str, str]:
        session = _require_session(request, sessions)
        async with session.lock:
            if session.current_draft is None or session.workflow_id is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="There is no Current draft",
                )
            if session.active_command is not None or session.confirmation_in_progress:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="An Active command is already in progress",
                )
            session.confirmation_in_progress = True

        try:
            await workflow.resume(session, confirmation)
        finally:
            session.confirmation_in_progress = False
        return {"status": "accepted"}

    return application


def _require_session(request: Request, sessions: SessionStore) -> BrowserSession:
    session = sessions.get(request.cookies.get(_SESSION_COOKIE))
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Open the UCS page before sending a request",
        )
    return session
