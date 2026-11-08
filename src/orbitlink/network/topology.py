"""Small dependency-free directed graph for dynamic communication links."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class LinkEdge:
    source: str
    target: str
    delay_s: float
    distance_m: float = 0.0
    quality_penalty: float = 0.0
    congestion_penalty: float = 0.0
    capacity_bps: float = 1e9
    available: bool = True
    link_type: str = "rf"

    def __post_init__(self) -> None:
        if min(self.delay_s, self.distance_m, self.quality_penalty, self.congestion_penalty) < 0:
            raise ValueError("edge costs and distance must be non-negative")
        if self.capacity_bps <= 0:
            raise ValueError("link capacity must be positive")

    def cost(self, strategy: str) -> float:
        if strategy == "minimum_delay":
            return self.delay_s
        if strategy == "link_quality":
            return self.delay_s + self.quality_penalty
        if strategy == "congestion_aware":
            return self.delay_s + self.congestion_penalty
        if strategy == "shortest_distance":
            return self.distance_m
        raise ValueError(f"unknown routing strategy: {strategy}")


class NetworkGraph:
    """A graph snapshot; rebuild or replace its edges as geometry changes."""

    def __init__(self, nodes: set[str] | None = None, edges: list[LinkEdge] | None = None) -> None:
        self.nodes = set(nodes or ())
        self.edges: dict[str, list[LinkEdge]] = {}
        for edge in edges or []:
            self.add_edge(edge)

    def add_edge(self, edge: LinkEdge) -> None:
        self.nodes.update((edge.source, edge.target))
        self.edges.setdefault(edge.source, []).append(edge)

    def shortest_path(self, source: str, target: str, *, strategy: str = "minimum_delay") -> tuple[list[str], float] | None:
        if source == target:
            return [source], 0.0
        queue: list[tuple[float, str]] = [(0.0, source)]
        best = {source: 0.0}
        previous: dict[str, str] = {}
        while queue:
            distance, node = heapq.heappop(queue)
            if distance != best.get(node):
                continue
            if node == target:
                path = [target]
                while path[-1] != source:
                    path.append(previous[path[-1]])
                return list(reversed(path)), distance
            for edge in self.edges.get(node, ()):
                if not edge.available:
                    continue
                cost = edge.cost(strategy)
                candidate = distance + cost
                if candidate < best.get(edge.target, math.inf):
                    best[edge.target] = candidate
                    previous[edge.target] = node
                    heapq.heappush(queue, (candidate, edge.target))
        return None

    def edges_for_path(self, path: list[str]) -> list[LinkEdge]:
        result = []
        for source, target in zip(path, path[1:]):
            edge = next((edge for edge in self.edges.get(source, ()) if edge.target == target and edge.available), None)
            if edge is None:
                raise ValueError(f"path contains unavailable edge {source}->{target}")
            result.append(edge)
        return result
