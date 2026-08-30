"""Black-box conformance corpus: 200 protocol-level cases for the Agent.

Everything here drives the agent through its *public contract only* --
`Agent(catalog)`, `reset`, `respond` -- plus the unmodified evaluator's own
message and scoring helpers. Nothing imports a private attribute or a module
that exists on only one branch, so the same corpus runs unchanged against any
revision of the agent and the results are directly comparable.

That is deliberate. `tests/test_agent_core.py`, `test_agent_hardening.py`,
`test_card_spec_parity.py` and `test_submission_bundle.py` are unit tests: they
reach into `IntentIndex.segment`, `_resolve`, `session_state` and the module
graph. Useful, but they can only ever confirm that the implementation does what
its author intended. This corpus asserts what the *protocol* requires,
independently of how the agent is built.
"""
