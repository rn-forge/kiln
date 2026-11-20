"""The catalogue of kiln's architecture records: IDs, titles and when each applies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from rn_forge.kiln.config import KilnConfig

__all__ = ["RECORDS", "Record", "records_for"]


@dataclass(frozen=True, slots=True)
class Record:
    """One architecture record: its ID, title and the configs it applies to."""

    id: str
    title: str
    applies: Callable[[KilnConfig], bool]


RECORDS: tuple[Record, ...] = (
    Record(
        "ARCH-0001",
        "Dependencies point inward; I/O lives at the edges",
        lambda config: not config.is_workspace and not config.is_node_lib,
    ),
    Record(
        "ARCH-0002",
        "Errors, settings and logs each cross one boundary",
        lambda config: not config.is_workspace and not config.is_node_lib,
    ),
    Record(
        "ARCH-0003",
        "A library's surface is explicit and inert",
        lambda config: config.is_workspace,
    ),
)


def records_for(config: KilnConfig) -> tuple[Record, ...]:
    """The records that apply to *config*, in `RECORDS` order; the docs profile is not read."""
    return tuple(record for record in RECORDS if record.applies(config))
