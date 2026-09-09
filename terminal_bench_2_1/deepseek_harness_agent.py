"""Harbor adapter for a pinned, host-mounted DeepSeek Harness runtime."""

from __future__ import annotations

from typing import override

from harbor.agents.installed.base import BaseInstalledAgent, with_prompt_template
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class DeepSeekHarnessEvalAgent(BaseInstalledAgent):
    """Run the official DeepSeek Harness without installing from the network."""

    TOOLCHAIN_ROOT = "/opt/deepseek-harness-toolchain"
    PROFILE_SOURCE = "/opt/deepseek-harness-profile"
    DSH_HOME = "/installed-agent/dsh-home"
    PROFILE_NAME = "quietbox2-eval"
    OUTPUT_PATH = "/logs/agent/deepseek-harness.txt"

    @staticmethod
    @override
    def name() -> str:
        return "deepseek-harness-eval"

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
                f"mkdir -p {profile_target} && "
                f"cp {self.PROFILE_SOURCE}/package.json {profile_target}/package.json && "
                f"cp {self.PROFILE_SOURCE}/cordis.yml {profile_target}/cordis.yml && "
                f"cp {self.PROFILE_SOURCE}/cordis.patch.yml {profile_target}/cordis.patch.yml && "
                f"chmod -R a+rX {self.DSH_HOME} && "
                "mkdir -p /logs/agent/dsh-sessions && "
                "chmod a+rwx /logs/agent/dsh-sessions"
            ),
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
            env={
                "DEEPSEEK_API_KEY": "EMPTY",
                "DEEPSEEK_BASE_URL": "http://host.docker.internal:8011/v1",
            },
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
                "DEEPSEEK_BASE_URL": "http://host.docker.internal:8011/v1",
                "DSH_PRESERVE_BACKGROUND_PROCESSES": "1",
                "DEBIAN_FRONTEND": "noninteractive",
                "TZ": "Etc/UTC",
                "NO_COLOR": "1",
            },
        )
