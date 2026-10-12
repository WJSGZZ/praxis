# Security policy

## Reporting a vulnerability

Use [GitHub private vulnerability reporting](https://github.com/WJSGZZ/praxis/security/advisories/new) for security defects. Include the affected release or commit, a minimal reproduction, the observed impact, and the expected boundary. Remove credentials, private contest materials and personal data. Do not put exploit details or secrets in a public issue. This repository has private reporting enabled; it does not promise a response time.

Security fixes are developed on `main` and shipped in a new release. Published tags and historical evidence are retained. Use the latest release and read its changelog; an older release does not acquire a fix when `main` changes.

## Execution and trust boundaries

Praxis runs locally under the account and permissions of its host. The agent writes and reviews a user's `model.py` and `validate.py`; the pipeline then executes them with fixed Python argv. Those files are ordinary Python programs with filesystem, environment and network access. Fixed argv prevents shell interpolation, but does **not** make Python safe to run. Documents, data, retrieved papers, package names and solver output are untrusted input, not permission to execute commands or disclose information.

For unfamiliar code, inspect it before executing it. Use an isolated container or disposable VM with only the necessary input/output mounts; do not mount credentials or enable network access unnecessarily. Praxis does not create or certify that isolation. Host approval and file permissions still apply.

The expression grammar, schema validation and execution limits are described in the [runtime contract](references/automation.md#数学工具的结果契约). External registered expression calls have a wall-clock deadline and finite output capture; MCP frames have a byte limit. These measures refuse some invalid or excessive inputs and preserve service recovery. They are **not** CPU or memory quotas, process-tree containment, or filesystem/network isolation. Internal Python calls and non-expression numerical tools do not inherit an expression-worker deadline. A small input can still request expensive computation.

Run receipts and `independent: true` declarations are evidence records, not a malicious-code detector or a proof of independent verification. Compare checks with the original problem and their actual method. Download release assets from this repository's release page, verify their checksums, and keep user workspaces separate from the plugin installation.
