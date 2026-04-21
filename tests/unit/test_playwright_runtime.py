"""Unit coverage for Crawl4AI Playwright runtime diagnostics."""

from pathlib import Path

from cortex_common import load_runtime_config
from cortex_parse import classify_crawl4ai_playwright_failure, resolve_crawl4ai_playwright_runtime


def test_classify_crawl4ai_playwright_failure_detects_missing_browser_binary() -> None:
    failure = classify_crawl4ai_playwright_failure(
        RuntimeError("BrowserType.launch: Executable doesn't exist at /tmp/chromium/chrome")
    )

    assert failure.code == "browser_binary_missing"
    assert any("install-if-missing" in hint for hint in failure.hints)


def test_classify_crawl4ai_playwright_failure_detects_host_process_policy_block() -> None:
    failure = classify_crawl4ai_playwright_failure(
        RuntimeError("PermissionError: [WinError 5] access is denied while create_subprocess_exec")
    )

    assert failure.code == "host_process_policy_blocked"
    assert any("Linux" in hint for hint in failure.hints)


def test_resolve_crawl4ai_playwright_runtime_prefers_container_env_overrides(
    monkeypatch,
) -> None:
    runtime_config = load_runtime_config("configs/cortex.runtime.local.yaml")
    override_base_directory = str((Path.cwd() / ".data" / "crawl4ai" / "container-test").resolve())

    monkeypatch.setenv("CORTEX_CRAWL4AI_BASE_DIRECTORY", override_base_directory)
    monkeypatch.setenv("CORTEX_PLAYWRIGHT_BROWSERS_PATH", "/ms-playwright")

    runtime = resolve_crawl4ai_playwright_runtime(runtime_config)

    assert runtime.base_directory == Path(override_base_directory)
    assert runtime.browsers_path == Path("/ms-playwright").resolve()
