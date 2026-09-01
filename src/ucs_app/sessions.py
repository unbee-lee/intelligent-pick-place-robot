"""Browser-session state and structured UCS activity events."""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Set
from uuid import uuid4


@dataclass(frozen=True)
class ActivityEvent:
    """One browser-safe event in the structured activity trail."""

    sequence: int
    kind: str
    message: str
    details: Mapping[str, object]

    def as_dict(self) -> Dict[str, object]:
        """Return the JSON-safe representation delivered through SSE."""

        return {
            "sequence": self.sequence,
            "kind": self.kind,
            "message": self.message,
            "details": dict(self.details),
        }

    def as_sse(self) -> str:
        """Encode the event as one Server-Sent Events data frame."""

        return f"id: {self.sequence}\ndata: {json.dumps(self.as_dict())}\n\n"


@dataclass
class BrowserSession:
    """UCS state belonging to one browser session."""

    session_id: str
    workflow_id: Optional[str] = None
    current_draft: Optional[Dict[str, object]] = None
    active_message_id: Optional[str] = None
    active_target: Optional[Dict[str, object]] = None
    last_successful_arrangement: Optional[Dict[str, object]] = None
    confirmation_in_progress: bool = False
    events: List[ActivityEvent] = field(default_factory=list)
    subscribers: Set[asyncio.Queue[ActivityEvent]] = field(default_factory=set)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionStore:
    """Own browser sessions and fan out their structured activity events."""

    def __init__(self) -> None:
        self._sessions: Dict[str, BrowserSession] = {}

    def create(self) -> BrowserSession:
        """Create a new isolated browser session."""

        session_id = str(uuid4())
        session = BrowserSession(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: Optional[str]) -> Optional[BrowserSession]:
        """Return an existing session without silently creating one."""

        if session_id is None:
            return None
        return self._sessions.get(session_id)

    def emit(
        self,
        session: BrowserSession,
        *,
        kind: str,
        message: str,
        details: Optional[Mapping[str, object]] = None,
    ) -> ActivityEvent:
        """Append and broadcast one browser-safe activity event."""

        event = ActivityEvent(
            sequence=len(session.events) + 1,
            kind=kind,
            message=message,
            details={} if details is None else dict(details),
        )
        session.events.append(event)
        for subscriber in session.subscribers:
            subscriber.put_nowait(event)
        return event

    def subscribe(self, session: BrowserSession) -> asyncio.Queue[ActivityEvent]:
        """Attach one SSE stream to a browser session."""

        subscriber: asyncio.Queue[ActivityEvent] = asyncio.Queue()
        session.subscribers.add(subscriber)
        return subscriber

    def unsubscribe(
        self,
        session: BrowserSession,
        subscriber: asyncio.Queue[ActivityEvent],
    ) -> None:
        """Detach a closed SSE stream."""

        session.subscribers.discard(subscriber)
