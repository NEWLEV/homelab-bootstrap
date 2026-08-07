from bootstrap.graph import build_dependency_graph, render_dependency_graph
from bootstrap.manifests import infrastructure_manifest


def test_build_dependency_graph_lists_nodes_and_edges() -> None:
    manifest = infrastructure_manifest()
    graph = build_dependency_graph(manifest)

    assert graph.name == "infrastructure"
    assert graph.nodes == ("reverse-proxy", "monitoring", "backups")
    assert graph.edges == (
        ("reverse-proxy", "monitoring"),
        ("monitoring", "backups"),
    )


def test_render_dependency_graph_returns_adjacency() -> None:
    manifest = infrastructure_manifest()
    graph = render_dependency_graph(manifest)

    assert graph["name"] == "infrastructure"
    assert graph["nodes"] == ["reverse-proxy", "monitoring", "backups"]
    assert graph["adjacency"]["reverse-proxy"] == ["monitoring"]
    assert graph["adjacency"]["monitoring"] == ["backups"]
