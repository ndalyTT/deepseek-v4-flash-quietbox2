# SPDX-FileCopyrightText: © 2026 Tenstorrent USA, Inc.
# SPDX-License-Identifier: Apache-2.0

"""One-shot canonical QuietBox fabric initialization and exact BF16 all-reduce smoke."""

import os

import torch

import ttnn


def main() -> None:
    trace_region_size = int(os.environ.get("TRACE_REGION_SIZE", "0"))
    router_payload_bytes = int(os.environ.get("ROUTER_PAYLOAD_BYTES", str(14 * 1024)))
    override_names = (
        "TT_MESH_GRAPH_DESC_PATH",
        "TT_METAL_DISABLE_MULTI_AERISC",
        "TT_METAL_DISABLE_FABRIC_TWO_ERISC",
    )
    print("SMOKE_START")
    for name in override_names:
        print(f"ENV_{name}={os.environ.get(name, '<ABSENT>')}")

    router_config = ttnn.FabricRouterConfig()
    router_config.max_packet_payload_size_bytes = router_payload_bytes
    mesh = None
    try:
        ttnn.set_fabric_config(
            ttnn.FabricConfig.FABRIC_1D_RING,
            ttnn.FabricReliabilityMode.RELAXED_INIT,
            None,
            ttnn.FabricTensixConfig.DISABLED,
            ttnn.FabricUDMMode.DISABLED,
            ttnn.FabricManagerMode.DEFAULT,
            router_config,
        )
        print(f"FABRIC_CONFIG={ttnn.get_fabric_config()}")
        print("RELIABILITY_MODE=RELAXED_INIT")
        print("FABRIC_TENSIX_CONFIG=DISABLED")
        print("FABRIC_UDM_MODE=DISABLED")
        print("FABRIC_MANAGER_MODE=DEFAULT")
        print(f"ROUTER_PAYLOAD_BYTES={router_config.max_packet_payload_size_bytes}")
        print("MESH_SHAPE=(4,1)")
        print("L1_SMALL_SIZE=2048")
        print(f"TRACE_REGION_SIZE={trace_region_size}")

        mesh = ttnn.open_mesh_device(
            mesh_shape=ttnn.MeshShape(4, 1),
            l1_small_size=2048,
            trace_region_size=trace_region_size,
        )
        print(f"MESH_OPEN_OK shape={tuple(mesh.shape)} devices={mesh.get_num_devices()}")

        host_input = torch.ones((1, 1, 32, 32), dtype=torch.bfloat16)
        device_input = ttnn.from_torch(
            host_input,
            dtype=ttnn.bfloat16,
            layout=ttnn.TILE_LAYOUT,
            device=mesh,
            mesh_mapper=ttnn.ReplicateTensorToMesh(mesh),
        )
        device_output = ttnn.all_reduce(device_input, cluster_axis=0)
        ttnn.synchronize_device(mesh)

        expected = host_input * mesh.get_num_devices()
        local_outputs = ttnn.get_device_tensors(device_output)
        exact_by_rank = []
        for rank, local_output in enumerate(local_outputs):
            host_output = ttnn.to_torch(local_output)
            exact = torch.equal(host_output, expected)
            exact_by_rank.append(exact)
            print(
                f"RANK_{rank}_EXACT={exact} shape={tuple(host_output.shape)} "
                f"unique={torch.unique(host_output).tolist()}"
            )
        if len(exact_by_rank) != 4 or not all(exact_by_rank):
            raise AssertionError(f"Exact BF16 all-reduce failed: {exact_by_rank}")
        print("COLLECTIVE_EXACT_OK ranks=4 expected_value=4.0")
        print("SMOKE_PASS")
    finally:
        try:
            if mesh is not None:
                ttnn.close_mesh_device(mesh)
                print("MESH_CLOSE_OK")
        finally:
            ttnn.set_fabric_config(ttnn.FabricConfig.DISABLED)
            print(f"FABRIC_DISABLED={ttnn.get_fabric_config()}")


if __name__ == "__main__":
    main()
