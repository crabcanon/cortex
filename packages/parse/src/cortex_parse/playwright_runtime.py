"""Crawl4AI Playwright runtime preparation helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from cortex_common import ConfigError, LoadedRuntimeConfig


@dataclass(frozen=True, slots=True)
class Crawl4AIPlaywrightRuntime:
    enabled: bool
    base_directory: Path
    browsers_path: Path
    browser_name: str
    validate_on_startup: bool


@dataclass(frozen=True, slots=True)
class Crawl4AIPlaywrightFailure:
    code: str
    hints: tuple[str, ...]


def resolve_crawl4ai_playwright_runtime(
    runtime_config: LoadedRuntimeConfig,
) -> Crawl4AIPlaywrightRuntime:
    config = runtime_config.config.parse.engines.crawl4ai
    base_directory = _resolve_runtime_path(
        _resolve_runtime_value(
            os.getenv("CORTEX_CRAWL4AI_BASE_DIRECTORY"),
            os.getenv("CRAWL4AI_BASE_DIRECTORY"),
            os.getenv("CRAWL4_AI_BASE_DIRECTORY"),
            runtime_config.resolve_reference(config.base_directory_ref),
        ),
        default=(Path.cwd() / ".data" / "crawl4ai"),
    )
    browsers_path = _resolve_runtime_path(
        _resolve_runtime_value(
            os.getenv("CORTEX_PLAYWRIGHT_BROWSERS_PATH"),
            os.getenv("PLAYWRIGHT_BROWSERS_PATH"),
            runtime_config.resolve_reference(config.playwright_browsers_path_ref),
        ),
        default=(Path.cwd() / ".data" / "playwright"),
    )
    browser_name = str(config.playwright_browser or "chromium").strip() or "chromium"
    return Crawl4AIPlaywrightRuntime(
        enabled=config.enabled,
        base_directory=base_directory,
        browsers_path=browsers_path,
        browser_name=browser_name,
        validate_on_startup=bool(config.playwright_validate_on_startup),
    )


def apply_crawl4ai_playwright_environment(runtime: Crawl4AIPlaywrightRuntime) -> None:
    _ensure_directory(
        runtime.base_directory,
        context=(
            "Unable to initialize the Crawl4AI base directory. "
            "Set `parse.engines.crawl4ai.base_directory_ref` to a writable path."
        ),
    )
    _ensure_directory(
        runtime.browsers_path,
        context=(
            "Unable to initialize the Playwright browsers directory for Crawl4AI. "
            "Set `parse.engines.crawl4ai.playwright_browsers_path_ref` to a writable path."
        ),
    )
    os.environ["CRAWL4_AI_BASE_DIRECTORY"] = str(runtime.base_directory)
    os.environ["CRAWL4AI_BASE_DIRECTORY"] = str(runtime.base_directory)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(runtime.browsers_path)


def install_playwright_browser(
    runtime: Crawl4AIPlaywrightRuntime,
    *,
    python_executable: str | None = None,
    with_deps: bool = False,
) -> None:
    apply_crawl4ai_playwright_environment(runtime)
    command = [python_executable or sys.executable, "-m", "playwright", "install"]
    if with_deps:
        command.append("--with-deps")
    command.append(runtime.browser_name)
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        output = _summarize_subprocess_output(completed.stdout, completed.stderr)
        raise ConfigError(
            "Failed to install the Playwright browser required by Crawl4AI. "
            f"Command exited with code {completed.returncode}: {' '.join(command)}"
            + (f" | Output: {output}" if output else "")
        )


def probe_playwright_browser(runtime: Crawl4AIPlaywrightRuntime) -> None:
    apply_crawl4ai_playwright_environment(runtime)
    completed = subprocess.run(
        [sys.executable, "-c", _probe_script(), runtime.browser_name],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        install_command = f"{sys.executable} -m playwright install {runtime.browser_name}"
        output = _summarize_subprocess_output(completed.stdout, completed.stderr)
        raise ConfigError(
            "Crawl4AI Playwright browser preflight failed. "
            f"Configured browser `{runtime.browser_name}` under "
            f"`{runtime.browsers_path}` could not launch. "
            f"Install or repair it with `{install_command}` and ensure the host permits "
            "Playwright child-process startup." + (f" | Output: {output}" if output else "")
        )


def prepare_crawl4ai_playwright_runtime(
    runtime_config: LoadedRuntimeConfig,
    *,
    install_if_missing: bool = False,
    with_deps: bool = False,
    probe: bool | None = None,
) -> Crawl4AIPlaywrightRuntime:
    runtime = resolve_crawl4ai_playwright_runtime(runtime_config)
    if not runtime.enabled:
        return runtime

    apply_crawl4ai_playwright_environment(runtime)
    should_probe = runtime.validate_on_startup if probe is None else probe
    if not should_probe:
        if install_if_missing:
            install_playwright_browser(runtime, with_deps=with_deps)
        return runtime

    try:
        probe_playwright_browser(runtime)
    except ConfigError:
        if not install_if_missing:
            raise
        install_playwright_browser(runtime, with_deps=with_deps)
        probe_playwright_browser(runtime)
    return runtime


def classify_crawl4ai_playwright_failure(
    error: BaseException,
) -> Crawl4AIPlaywrightFailure:
    text = _exception_text(error).lower()

    if any(
        token in text
        for token in (
            "spawn eperm",
            "winerror 5",
            "access is denied",
            "拒绝访问",
            "create_subprocess_exec",
            "named pipe",
        )
    ):
        return Crawl4AIPlaywrightFailure(
            code="host_process_policy_blocked",
            hints=(
                "当前宿主机阻止了 Playwright / Node 子进程或命名管道。"
                "请在原生 PowerShell、CMD 或 Linux 容器中验证，"
                "而不要只依赖受限 IDE 终端。",
                "Windows 上需检查 Defender、AppLocker、组策略或企业安全软件"
                "是否拦截 Playwright 子进程；若无法放开，建议把 Crawl4AI 固定"
                "运行在预装浏览器的 Linux 容器中。",
            ),
        )

    if any(
        token in text
        for token in (
            "executable doesn't exist",
            "missing browser",
            "playwright browser required",
            "failed to install the playwright browser required by crawl4ai",
        )
    ):
        return Crawl4AIPlaywrightFailure(
            code="browser_binary_missing",
            hints=(
                "在目标部署环境先执行 "
                "`python scripts/runtime/prepare_crawl4ai_runtime.py --install-if-missing`，"
                "不要等首个请求再懒安装浏览器。",
                "如果走容器部署，请在镜像构建阶段预装浏览器，"
                "并让 API / Parse Worker 启动时只做预检、不做现场下载。",
            ),
        )

    if any(
        token in text
        for token in (
            "missing dependencies",
            "--with-deps",
            "install-deps",
            "host system is missing dependencies",
        )
    ):
        return Crawl4AIPlaywrightFailure(
            code="host_browser_dependencies_missing",
            hints=(
                "浏览器二进制已存在，但宿主机缺少 Playwright 所需的系统依赖。"
                "Linux 镜像或主机请在准备阶段执行 `--with-deps`。",
                "生产环境不要把系统依赖安装留到运行时，"
                "应该在镜像构建阶段完成浏览器与系统依赖预装。",
            ),
        )

    if "certificate" in text and any(token in text for token in ("download", "ssl", "tls")):
        return Crawl4AIPlaywrightFailure(
            code="browser_download_tls_failed",
            hints=(
                "浏览器下载阶段遇到了 TLS / 证书链问题。请在目标环境补齐"
                "受信任 CA，或通过企业代理 / 制品仓库提供浏览器下载镜像。",
                "若在内网构建镜像，建议在 CI/CD 构建阶段完成浏览器下载，"
                "并将镜像作为唯一发布制品，而不是在运行时联网下载。",
            ),
        )

    return Crawl4AIPlaywrightFailure(
        code="playwright_runtime_preflight_failed",
        hints=(
            "请先运行 `python scripts/runtime/prepare_crawl4ai_runtime.py --json` "
            "查看统一运行时配置解析结果，再决定是修配置、补浏览器还是"
            "调整宿主机权限。",
            "生产部署建议使用仓内的容器化入口或预启动脚本，"
            "把浏览器准备放到发布前置步骤，而不是留给首个在线请求。",
        ),
    )


def _resolve_runtime_path(path_value: str | None, *, default: Path) -> Path:
    raw = path_value.strip() if isinstance(path_value, str) else ""
    target = Path(raw) if raw else default
    return target.expanduser().resolve()


def _resolve_runtime_value(*candidates: str | None) -> str | None:
    for candidate in candidates:
        if isinstance(candidate, str):
            value = candidate.strip()
            if value:
                return value
    return None


def _ensure_directory(path: Path, *, context: str) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigError(context) from exc


def _exception_text(error: BaseException) -> str:
    messages: list[str] = []
    current: BaseException | None = error
    seen: set[int] = set()

    while current is not None and id(current) not in seen:
        seen.add(id(current))
        text = str(current).strip()
        if text:
            messages.append(text)
        current = current.__cause__ or current.__context__

    return " | ".join(messages)


def _summarize_subprocess_output(stdout: str | None, stderr: str | None) -> str:
    parts = [segment.strip() for segment in (stderr, stdout) if isinstance(segment, str)]
    joined = " | ".join(part for part in parts if part)
    collapsed = " ".join(joined.split())
    if len(collapsed) <= 500:
        return collapsed
    return f"{collapsed[:497]}..."


def _probe_script() -> str:
    return (
        "import sys\n"
        "from playwright.sync_api import sync_playwright\n"
        "browser_name = sys.argv[1]\n"
        "with sync_playwright() as playwright:\n"
        "    browser_type = getattr(playwright, browser_name, None)\n"
        "    if browser_type is None:\n"
        "        raise SystemExit(f'Unsupported Playwright browser: {browser_name}')\n"
        "    browser = browser_type.launch(headless=True)\n"
        "    browser.close()\n"
    )
