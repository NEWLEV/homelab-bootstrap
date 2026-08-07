from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .infrastructure import InfrastructureManifest, network_plan, storage_plan


@dataclass(frozen=True)
class StorageNetworkPlan:
    storage: dict[str, Any]
    networking: dict[str, Any]


def build_storage_network_plan(manifest: InfrastructureManifest) -> StorageNetworkPlan:
    storage = storage_plan(manifest)
    networking = network_plan(manifest)
    return StorageNetworkPlan(
        storage={
            "root": storage.root,
            "volumes": list(storage.volumes),
            "volume_paths": {
                volume: f"{storage.root}/{volume}"
                for volume in storage.volumes
            },
        },
        networking={
            "networks": list(networking.networks),
            "reverse_proxy_network": networking.reverse_proxy_network,
            "internal_networks": [
                network for network in networking.networks if network != networking.reverse_proxy_network
            ],
            "boundaries": {
                "public": [networking.reverse_proxy_network],
                "private": [network for network in networking.networks if network != networking.reverse_proxy_network],
            },
        },
    )


def render_storage_network_plan(manifest: InfrastructureManifest) -> dict[str, Any]:
    plan = build_storage_network_plan(manifest)
    return {
        "storage": plan.storage,
        "networking": plan.networking,
    }
