# Potentially related official Tenstorrent references

These references may help route the case. They do not prove the root cause.

1. Blackhole active Ethernet-core timeout with earlier firmware-init failure:
   https://github.com/tenstorrent/tt-metal/issues/25553
   - Reports `Eth mailbox timeout waiting for active eth core` on Blackhole.
   - One linked occurrence had the earlier error `Device 0 init: failed to initialize FW! Try resetting the board.`
   - Closed as a duplicate of #25427.

2. Blackhole multi-chip ERISC0 instability:
   https://github.com/tenstorrent/tt-metal/issues/25427
   - Describes back-to-back Ethernet API hangs involving ERISC0 on Blackhole multi-chip systems.
   - Notes that failures become more likely as systems are connected and that slow dispatch was more likely to succeed.

3. TT-Fabric configuration documentation:
   https://github.com/tenstorrent/tt-metal/blob/main/tech_reports/Programming_Multiple_Meshes/Programming_Multiple_Meshes.md
   - Documents `FABRIC_1D_RING`, `STRICT_INIT`, `RELAXED_INIT`, and the requirement to set fabric before opening the mesh.

4. System firmware releases:
   https://github.com/tenstorrent/tt-system-firmware/releases
   - 19.11.0 updated Blackhole ERISC firmware to 1.11.0.
   - 19.12.0 updated it to 1.12.0 and reworked runtime link-check and recovery behavior.

5. tt-flash official repository and v3.10.0 source:
   https://github.com/tenstorrent/tt-flash
   https://raw.githubusercontent.com/tenstorrent/tt-flash/v3.10.0/tt_flash/main.py
   - The local `verify` crash matches an apparent parser path that accesses `args.download` although `download` is defined only on the `flash` subparser.
