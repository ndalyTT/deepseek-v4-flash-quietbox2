# Provenance

This profile is derived from Apache Maka's `deepseek-harness-profile` at
commit `ff226aff2f3082e54300dea0ee9e410898ae2c0f` (Apache-2.0), which in turn
derives its minimal composition, persistent-Bash description, and persona
from DeepSeek Harness commit `47f943859bef60e4160492346772ded9b24f765a`
(MIT). The pinned runtime is `@deepseek-ai/dsh@0.1.0-rc.6` with fingerprint
`sha256:9a7c0851d0a4f1f985971bbd2f0eb0455ca22ed6b9d2081b2eba9b9574d49833`.

Local non-model-visible changes relocate session logs under Harbor's log
mount. Provider/runtime changes select maximum reasoning, cap a single output
at 49,152 tokens within the deployed 131,072-token context, and extend Bash
command timeouts so they do not bind normal Terminal-Bench package setup.
