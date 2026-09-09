"""Harbor adapter for DeepSeek Harness over a mounted Unix-socket relay."""

from __future__ import annotations

from typing import override

from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class DeepSeekHarnessUnixEvalAgent(BaseInstalledAgent):
    """Run pinned DeepSeek Harness with no network install or host network."""

    TOOLCHAIN_ROOT = "/opt/deepseek-harness-toolchain"
    PROFILE_SOURCE = "/opt/deepseek-harness-profile"
    BRIDGE_SOURCE = "/opt/deepseek-harness-container-bridge.js"
    RELAY_SOCKET = "/opt/deepseek-relay-runtime/vllm_relay.sock"
    DSH_HOME = "/installed-agent/dsh-home"
    PROFILE_NAME = "quietbox2-eval"
    OUTPUT_PATH = "/logs/agent/deepseek-harness.txt"
    BASE_URL = "http://127.0.0.1:8011/v1"

    @staticmethod
    @override
    def name() -> str:
        return "deepseek-harness-unix-eval"

    @override
    def get_version_command(self) -> str | None:
        return (
            f"{self.TOOLCHAIN_ROOT}/bin/node "
            f"{self.TOOLCHAIN_ROOT}/lib/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js "
            "--version"
        )

    @override
    async def install(self, environment: BaseEnvironment) -> None:
        profile_target = f"{self.DSH_HOME}/profiles/{self.PROFILE_NAME}"
        await self.exec_as_root(
            environment,
            command=(
                f"test -x {self.TOOLCHAIN_ROOT}/bin/node && "
                f"test -f {self.TOOLCHAIN_ROOT}/manifest.json && "
                f"test -f {self.PROFILE_SOURCE}/cordis.patch.yml && "
                f"test -f {self.BRIDGE_SOURCE} && "
                f"test -S {self.RELAY_SOCKET} && "
                f"mkdir -p {profile_target} && "
                f"cp {self.PROFILE_SOURCE}/package.json {profile_target}/package.json && "
                f"cp {self.PROFILE_SOURCE}/cordis.yml {profile_target}/cordis.yml && "
                f"cp {self.PROFILE_SOURCE}/cordis.patch.yml {profile_target}/cordis.patch.yml && "
                f"chmod -R a+rX {self.DSH_HOME} && "
                "mkdir -p /logs/agent/dsh-sessions && "
                "chmod a+rwx /logs/agent/dsh-sessions && "
                f"nohup {self.TOOLCHAIN_ROOT}/bin/node {self.BRIDGE_SOURCE} "
                ">/logs/agent/deepseek-relay-bridge.txt 2>&1 & "
                "echo $! >/installed-agent/deepseek-relay-bridge.pid && "
                "for attempt in $(seq 1 50); do "
                "  if grep -q DSH_RELAY_BRIDGE_READY /logs/agent/deepseek-relay-bridge.txt; then exit 0; fi; "
                "  if ! kill -0 $(cat /installed-agent/deepseek-relay-bridge.pid) 2>/dev/null; then "
                "    cat /logs/agent/deepseek-relay-bridge.txt >&2; exit 1; "
                "  fi; "
                "  sleep 0.1; "
                "done; "
                "cat /logs/agent/deepseek-relay-bridge.txt >&2; exit 1"
            ),
            env={"DSH_RELAY_SOCKET": self.RELAY_SOCKET, "DSH_RELAY_PORT": "8011"},
        )

        await self.exec_as_agent(
            environment,
            command=(
                f"DSH_HOME={self.DSH_HOME} "
                f"{self.TOOLCHAIN_ROOT}/bin/node "
                f"{self.TOOLCHAIN_ROOT}/lib/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js "
                f"--profile {self.PROFILE_NAME} "
                "--dump-config >/logs/agent/deepseek-harness-config.json"
            ),
            env={"DEEPSEEK_API_KEY": "EMPTY", "DEEPSEEK_BASE_URL": self.BASE_URL},
        )

    @override
    @with_prompt_template
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        del context
        await self.exec_as_agent(
            environment,
            command=(
                "kill -0 $(cat /installed-agent/deepseek-relay-bridge.pid) && "
                'dsh_task="$DSH_TASK"; unset DSH_TASK; '
                f"{self.TOOLCHAIN_ROOT}/bin/node "
                f"{self.TOOLCHAIN_ROOT}/lib/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js "
                f'--profile {self.PROFILE_NAME} -- "$dsh_task" '
                f"</dev/null 2>&1 | tee {self.OUTPUT_PATH}"
            ),
            env={
                "DSH_TASK": instruction,
                "DSH_HOME": self.DSH_HOME,
                "DEEPSEEK_API_KEY": "EMPTY",
                "DEEPSEEK_BASE_URL": self.BASE_URL,
                "DSH_PRESERVE_BACKGROUND_PROCESSES": "1",
                "DEBIAN_FRONTEND": "noninteractive",
                "TZ": "Etc/UTC",
                "NO_COLOR": "1",
            },
        )
