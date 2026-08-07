from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest


@dataclass(frozen=True)
class DependencyGraph:
    name: str
    nodes: tuple[str, ...]
    edges: tuple[tuple[str, str], ...]


def build_dependency_graph(manifest: InfrastructureManifest) -> DependencyGraph:
    nodes = tuple(service.name for service in manifest.services)
    edges = tuple(
        (dependency, service.name)
        for service in manifest.services
        for dependency in service.depends_on
    )
    return DependencyGraph(name=manifest.name, nodes=nodes, edges=edges)


def render_dependency_graph(manifest: InfrastructureManifest) -> dict[str, Any]:
    graph = build_dependency_graph(manifest)
    return {
        "name": graph.name,
        "nodes": list(graph.nodes),
        "edges": [{"from": source, "to": target} for source, target in graph.edges],
        "adjacency": {
            node: sorted(
                target
                for source, target in graph.edges
                if source == node
            )
            for node in graph.nodes
        },
    }
