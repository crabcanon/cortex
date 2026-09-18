## 2024-05-15 - [Sentinel] Possible hardcoded passwords in test integration token responses
**Vulnerability:** Found `token_format = "dev"` and similar in auth tests flagged by Ruff (S105). Same for `token_type = "Bearer"` in the DevAuth contracts.
**Learning:** These are literal type constraints and default fields for a Pydantic model (`Literal["Bearer"] = "Bearer"`), not actual hardcoded secrets or passwords.
**Prevention:** It is safe to ignore or not journal these specific Ruff S105 false positives when they are defining a literal default in a schema.
## 2024-05-15 - [Sentinel] Allowed schemes in CI stack readiness checks
**Vulnerability:** Found `urllib.request.urlopen(target)` in `scripts/ci/wait_for_runtime_stack.py` flagged by Ruff (S310). The concern is opening arbitrary URLs such as `file:` schemes.
**Learning:** This script is for CI readiness checks to hit local docker container endpoints (like otel collector, minio, jaeger). The target URLs are parsed from env vars with defaults pointing to local `http://127.0.0.1` endpoints. While it is good practice to enforce `http` or `https` schemes, this is an internal CI script so the risk is low, but can be improved.
**Prevention:** It is safe to use `urllib.request.urlopen` in local CI checking scripts if it checks for `http` or `https` schemes.
## 2024-05-15 - [Sentinel] Use of insecure temporary file in graph visualization
**Vulnerability:** The script `examples/tensorzero-cortex/src/knowledge_graph_visualization.py` uses an insecure temporary file location `/tmp/cortex_knowledge_graph_...html` to dump a rendering script and run it in a container.
**Learning:** This is a temporary file inside a docker container. It is a potential risk but since it is inside a docker container generated specifically for rendering graphs, the blast radius is minimal, although an attacker with access to the container could potentially intercept the HTML before it is copied out. Using standard secure temporary file generation could be better, but the context is an example script. We can safely ignore this S108 given the script context (containerized demo script) but could fix it if no other better issues exist.
**Prevention:** Consider using tempfile standard library.
## 2024-05-15 - [Sentinel] Use of subprocess.run without check=True or untrusted input check
**Vulnerability:** Several places use `subprocess.run` (S603). `examples/tensorzero-cortex/src/knowledge_graph_visualization.py`, `scripts/ci/check.py`, `packages/parse/src/cortex_parse/playwright_runtime.py`.
**Learning:** These are all executing either local python scripts (`sys.executable, "-c", ...`) or docker commands with trusted paths and hardcoded commands. They are not taking raw user input.
**Prevention:** S603 is a good alert but in this case these are controlled environment scripts or hardcoded API calls, so no security risk. We can ignore.
## 2024-05-15 - [Sentinel] Missing Security Headers
**Vulnerability:** The API middleware `apps/api/src/cortex_api/middleware/request_context.py` acts as a global response handler but does not inject baseline API security headers (e.g. `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`).
**Learning:** This is a FastAPI app, and adding security headers is a standard defense-in-depth practice. The prompt explicitly mentions "Missing security headers (CSP, X-Frame-Options, etc.)" under HIGH PRIORITY and "Add security headers to responses" under MEDIUM.
**Prevention:** Always include baseline security headers in web APIs to prevent MIME sniffing and clickjacking, and to enforce TLS.
