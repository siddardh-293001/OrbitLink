"""Deterministic packet and queue accounting for network experiments."""

from __future__ import annotations

from dataclasses import dataclass

from orbitlink.network.topology import NetworkGraph


@dataclass(frozen=True)
class Packet:
    packet_id: str
    source: str
    destination: str
    size_bytes: int
    generated_at_s: float

    def __post_init__(self) -> None:
        if self.size_bytes <= 0 or self.generated_at_s < 0:
            raise ValueError("packet size must be positive and generation time non-negative")


@dataclass(frozen=True)
class PacketOutcome:
    packet_id: str
    delivered: bool
    route: tuple[str, ...]
    latency_s: float | None
    reason: str


@dataclass(frozen=True)
class TrafficMetrics:
    packets_generated: int
    packets_delivered: int
    packets_lost: int
    delivery_ratio: float
    throughput_bps: float
    mean_latency_s: float | None
    outcomes: tuple[PacketOutcome, ...]


def simulate_packets(packets: list[Packet], graph: NetworkGraph, *, routing_strategy: str = "minimum_delay") -> TrafficMetrics:
    """Run store-and-forward packets using per-edge FIFO availability clocks."""
    edge_ready_at: dict[tuple[str, str], float] = {}
    outcomes = []
    for packet in sorted(packets, key=lambda x: (x.generated_at_s, x.packet_id)):
        route_result = graph.shortest_path(packet.source, packet.destination, strategy=routing_strategy)
        if route_result is None:
            outcomes.append(PacketOutcome(packet.packet_id, False, (), None, "no available route"))
            continue
        path, _ = route_result
        arrival = packet.generated_at_s
        for edge in graph.edges_for_path(path):
            key = (edge.source, edge.target)
            start = max(arrival, edge_ready_at.get(key, 0.0))
            serialization = packet.size_bytes * 8 / edge.capacity_bps
            edge_ready_at[key] = start + serialization
            arrival = start + serialization + edge.delay_s
        outcomes.append(PacketOutcome(packet.packet_id, True, tuple(path), arrival - packet.generated_at_s, "delivered"))
    delivered = [outcome for outcome in outcomes if outcome.delivered]
    byte_count = sum(packet.size_bytes for packet in packets if any(x.packet_id == packet.packet_id and x.delivered for x in delivered))
    end_time = max((packet.generated_at_s for packet in packets), default=0.0)
    final_arrival = max((p.generated_at_s + (o.latency_s or 0) for p in packets for o in outcomes if p.packet_id == o.packet_id and o.delivered), default=end_time)
    span = max(final_arrival - min((p.generated_at_s for p in packets), default=0), 1e-12)
    count = len(packets)
    return TrafficMetrics(count, len(delivered), count - len(delivered), len(delivered) / count if count else 0.0,
                          byte_count * 8 / span if count else 0.0,
                          sum(o.latency_s for o in delivered) / len(delivered) if delivered else None,
                          tuple(outcomes))
