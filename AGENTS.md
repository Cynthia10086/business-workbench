# Local business workbench

This repository contains a local workbench and a portable business reasoning skill. It does not configure or call a model service. Use the host Agent for reasoning.

1. Read `skills/business-reasoning/SKILL.md` when analyzing an operating problem. Load only relevant scenario references.
2. Discover the runtime contract with `python3 workbench/cli.py tools-list`. CLI command names and MCP tool names are identical. Supply one JSON argument object via `--payload` or `--payload-file`.
3. Use an explicit user workspace outside this repository. Do not put private knowledge, cases, imported originals, credentials, or generated workspaces in the product tree. A project-level instruction from the user may specify the existing workspace; reuse it when appropriate.
4. Preserve original messages and sources. Retrieve relevant methods and evidence before updating a case. Use `state_update` with the current `expected_revision`; do not bypass semantic validation by editing SQLite directly.
5. Read `workbench/schemas/state.schema.json` before constructing state. Use observed IDs, verify quotations, keep counterevidence and explain revisions. A method is an analytical frame, not proof that a business event happened.
6. Use `context_assemble` to gather bounded context and inspect its omissions. Read omitted records separately if they could change the decision.
7. Publishing or synchronizing this product does not authorize publishing a user's workspace. Keep any release within the requested product scope.

For implementation changes, run meaningful tests with `python3 -m unittest discover -s workbench/tests -v`.
