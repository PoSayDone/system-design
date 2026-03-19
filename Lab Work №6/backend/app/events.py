from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass(slots=True)
class DomainEvent:
    name: str
    payload: dict[str, Any]
    occurred_at: datetime


class EventSubscriber(Protocol):
    def notify(self, event: DomainEvent) -> None: ...


class DomainEventPublisher:
    def __init__(self) -> None:
        self._subscribers: list[EventSubscriber] = []

    def subscribe(self, subscriber: EventSubscriber) -> None:
        self._subscribers.append(subscriber)

    def publish(self, name: str, payload: dict[str, Any]) -> None:
        event = DomainEvent(
            name=name,
            payload=payload,
            occurred_at=datetime.now(timezone.utc),
        )
        for subscriber in self._subscribers:
            subscriber.notify(event)


class AuditLogSubscriber:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def notify(self, event: DomainEvent) -> None:
        self.events.append(event)
