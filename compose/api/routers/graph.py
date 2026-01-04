"""Graph REST API router for knowledge graph visualization."""

from fastapi import APIRouter, HTTPException

from compose.services.notes import get_note_service
from compose.services.vaults import get_vault_service
from compose.services.surrealdb.models import GraphData

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/{vault_id}", response_model=GraphData)
async def get_graph(vault_id: str):
    """Get full graph data for a vault.

    Returns nodes (notes) and edges (wiki-links) for visualization.
    """
    # Verify vault exists
    vault_service = get_vault_service()
    vault = await vault_service.get_vault(vault_id)

    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    note_service = get_note_service()
    graph_data = await note_service.get_graph_data(vault_id)

    return graph_data


@router.get("/{vault_id}/local/{note_id}", response_model=GraphData)
async def get_local_graph(vault_id: str, note_id: str, depth: int = 2):
    """Get local graph centered on a specific note.

    Returns nodes within N hops of the specified note.
    """
    # Verify vault exists
    vault_service = get_vault_service()
    vault = await vault_service.get_vault(vault_id)

    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    note_service = get_note_service()

    # Verify note exists
    note = await note_service.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Get full graph and filter to local neighborhood
    # For now, return full graph - can optimize later with recursive query
    full_graph = await note_service.get_graph_data(vault_id)

    # Find nodes within depth hops of note_id
    connected_ids = {note_id}
    frontier = {note_id}

    for _ in range(depth):
        new_frontier = set()
        for edge in full_graph.edges:
            if edge.source in frontier:
                new_frontier.add(edge.target)
            if edge.target in frontier:
                new_frontier.add(edge.source)
        connected_ids.update(new_frontier)
        frontier = new_frontier - connected_ids

    # Filter graph to connected nodes
    local_nodes = [n for n in full_graph.nodes if n.id in connected_ids]
    local_edges = [
        e for e in full_graph.edges
        if e.source in connected_ids and e.target in connected_ids
    ]

    return GraphData(nodes=local_nodes, edges=local_edges)


@router.get("/{vault_id}/stats")
async def get_graph_stats(vault_id: str):
    """Get graph statistics for a vault."""
    # Verify vault exists
    vault_service = get_vault_service()
    vault = await vault_service.get_vault(vault_id)

    if not vault:
        raise HTTPException(status_code=404, detail="Vault not found")

    note_service = get_note_service()
    graph_data = await note_service.get_graph_data(vault_id)

    # Calculate stats
    node_count = len(graph_data.nodes)
    edge_count = len(graph_data.edges)

    # Find orphans (no connections)
    connected_ids = set()
    for edge in graph_data.edges:
        connected_ids.add(edge.source)
        connected_ids.add(edge.target)

    orphan_count = sum(
        1 for node in graph_data.nodes
        if node.id not in connected_ids
    )

    # Find most connected
    connection_counts: dict[str, int] = {}
    for edge in graph_data.edges:
        connection_counts[edge.source] = connection_counts.get(edge.source, 0) + 1
        connection_counts[edge.target] = connection_counts.get(edge.target, 0) + 1

    most_connected = []
    if connection_counts:
        sorted_nodes = sorted(
            connection_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]
        for node_id, count in sorted_nodes:
            node = next(
                (n for n in graph_data.nodes if n.id == node_id),
                None,
            )
            if node:
                most_connected.append({
                    "id": node_id,
                    "title": node.title,
                    "connections": count,
                })

    return {
        "node_count": node_count,
        "edge_count": edge_count,
        "orphan_count": orphan_count,
        "density": edge_count / (node_count * (node_count - 1) / 2)
        if node_count > 1
        else 0,
        "most_connected": most_connected,
    }
