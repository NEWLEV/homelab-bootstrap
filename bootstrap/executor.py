from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable

from .infrastructure import InfrastructureManifest, ManifestValidationError, network_plan, render_compose_plan, storage_plan, topological_service_order


@dataclass(frozen=True)
class PhaseResult:
    name: str
    started_at: float
    finished_at: float
    status: str
    detail: str | None = None

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at


@dataclass(frozen=True)
class PhaseExecutionSummary:
    phase_name: str
    results: tuple[PhaseResult, ...] = field(default_factory=tuple)

    @property
    def total_duration_seconds(self) -> float:
        return sum(result.duration_seconds for result in self.results)


PhaseHandler = Callable[[str, dict[str, Any]], str | None]


@dataclass(frozen=True)
class InfrastructurePhase:
    name: str
    description: str


PHASES: tuple[InfrastructurePhase, ...] = (
    InfrastructurePhase(
        name="storage",
        description="Provision and validate persistent storage.",
    ),
    InfrastructurePhase(
        name="networking",
        description="Define internal and exposed service networks.",
    ),
    InfrastructurePhase(
        name="monitoring",
        description="Prepare metrics, logging, and alerting services.",
    ),
    InfrastructurePhase(
        name="backups",
        description="Prepare backup and restore workflows.",
    ),
)


def infrastructure_phase_names() -> tuple[str, ...]:
    return tuple(phase.name for phase in PHASES)


def infrastructure_phase_descriptions() -> dict[str, str]:
    return {phase.name: phase.description for phase in PHASES}


def build_phase_payload(manifest: InfrastructureManifest) -> dict[str, Any]:
    return {
        "manifest": manifest,
        "compose": render_compose_plan(manifest),
        "storage": storage_plan(manifest),
        "networking": network_plan(manifest),
        "service_order": topological_service_order(manifest),
        "phases": infrastructure_phase_descriptions(),
    }


def run_infrastructure_phases(
    manifest: InfrastructureManifest,
    *,
    phase_handler: PhaseHandler | None = None,
) -> PhaseExecutionSummary:
    results: list[PhaseResult] = []
    phase_handler = phase_handler or (lambda phase_name, payload: None)
    payload = build_phase_payload(manifest)

    for phase in PHASES:
        started_at = perf_counter()
        try:
            detail = phase_handler(phase.name, payload)
            status = "completed"
        except ManifestValidationError as exc:
            detail = str(exc)
            status = "failed"
            finished_at = perf_counter()
            results.append(
                PhaseResult(
                    name=phase.name,
                    started_at=started_at,
                    finished_at=finished_at,
                    status=status,
                    detail=detail,
                )
            )
            raise
        finished_at = perf_counter()
        results.append(
            PhaseResult(
                name=phase.name,
                started_at=started_at,
                finished_at=finished_at,
                status=status,
                detail=detail,
            )
        )

    return PhaseExecutionSummary(
        phase_name=manifest.name,
        results=tuple(results),
    )
