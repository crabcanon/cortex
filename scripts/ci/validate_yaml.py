"""Validate published YAML configuration and OpenAPI assets."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


class ValidationError(RuntimeError):
    """Raised when a YAML or OpenAPI asset violates the expected contract."""


def _load_yaml(relative_path: str) -> object:
    path = REPO_ROOT / relative_path
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8-sig")

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValidationError(f"{relative_path}: YAML parse failed: {exc}") from exc


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _mapping(value: object, label: str) -> Mapping[str, object]:
    _expect(isinstance(value, Mapping), f"{label} must be a mapping.")
    return value


def _string(value: object, label: str) -> str:
    _expect(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string.")
    return value.strip()


def _string_list(value: object, label: str) -> list[str]:
    _expect(isinstance(value, list), f"{label} must be a list.")
    normalized: list[str] = []
    for index, item in enumerate(value):
        normalized.append(_string(item, f"{label}[{index}]"))
    return normalized


def _is_bilingual(value: str) -> bool:
    parts = re.split(r"\s+/\s+", value, maxsplit=1)
    if len(parts) != 2:
        return False
    english, translated = parts
    return bool(english.strip()) and bool(translated.strip())


def _validate_bilingual_text(value: object, label: str) -> None:
    text = _string(value, label)
    _expect(
        _is_bilingual(text),
        f"{label} must include both English and Chinese text separated by ' / '.",
    )


def _validate_openapi() -> None:
    document = _mapping(_load_yaml("specs/cortex-api.yaml"), "specs/cortex-api.yaml")
    openapi_version = _string(document.get("openapi"), "specs/cortex-api.yaml.openapi")
    _expect(
        openapi_version.startswith("3."),
        "specs/cortex-api.yaml.openapi must target OpenAPI 3.x.",
    )

    info = _mapping(document.get("info"), "specs/cortex-api.yaml.info")
    _string(info.get("title"), "specs/cortex-api.yaml.info.title")
    _string(info.get("version"), "specs/cortex-api.yaml.info.version")
    _validate_bilingual_text(info.get("summary"), "specs/cortex-api.yaml.info.summary")
    _string(info.get("description"), "specs/cortex-api.yaml.info.description")

    servers = document.get("servers", [])
    _expect(
        isinstance(servers, list) and servers,
        "specs/cortex-api.yaml.servers must be a non-empty list.",
    )
    for index, server in enumerate(servers):
        server_mapping = _mapping(server, f"specs/cortex-api.yaml.servers[{index}]")
        _string(server_mapping.get("url"), f"specs/cortex-api.yaml.servers[{index}].url")
        _validate_bilingual_text(
            server_mapping.get("description"),
            f"specs/cortex-api.yaml.servers[{index}].description",
        )

    tags = document.get("tags", [])
    _expect(isinstance(tags, list) and tags, "specs/cortex-api.yaml.tags must be a non-empty list.")
    for index, tag in enumerate(tags):
        tag_mapping = _mapping(tag, f"specs/cortex-api.yaml.tags[{index}]")
        _string(tag_mapping.get("name"), f"specs/cortex-api.yaml.tags[{index}].name")
        _validate_bilingual_text(
            tag_mapping.get("description"),
            f"specs/cortex-api.yaml.tags[{index}].description",
        )

    paths = _mapping(document.get("paths"), "specs/cortex-api.yaml.paths")
    _expect(paths, "specs/cortex-api.yaml.paths must not be empty.")
    operation_ids: set[str] = set()
    for path_name, path_item in paths.items():
        path_mapping = _mapping(path_item, f"specs/cortex-api.yaml.paths[{path_name!r}]")
        for method_name, operation in path_mapping.items():
            if str(method_name).startswith("x-"):
                continue
            operation_mapping = _mapping(
                operation,
                f"specs/cortex-api.yaml.paths[{path_name!r}].{method_name}",
            )
            operation_id = _string(
                operation_mapping.get("operationId"),
                f"specs/cortex-api.yaml.paths[{path_name!r}].{method_name}.operationId",
            )
            _expect(
                operation_id not in operation_ids,
                f"Duplicate OpenAPI operationId detected: {operation_id}.",
            )
            operation_ids.add(operation_id)
            if "summary" in operation_mapping:
                pass

            if "description" in operation_mapping:
                _validate_bilingual_text(
                    operation_mapping.get("description"),
                    f"specs/cortex-api.yaml.paths[{path_name!r}].{method_name}.description",
                )

            responses = _mapping(
                operation_mapping.get("responses"),
                f"specs/cortex-api.yaml.paths[{path_name!r}].{method_name}.responses",
            )
            _expect(
                responses,
                "specs/cortex-api.yaml.paths"
                f"[{path_name!r}].{method_name}.responses must not be empty.",
            )
            for status_code, response in responses.items():
                if not isinstance(response, Mapping):
                    raise ValidationError(
                        "specs/cortex-api.yaml.paths"
                        f"[{path_name!r}].{method_name}.responses[{status_code!r}]"
                        " must be a mapping."
                    )
                if "$ref" in response:
                    continue
                _validate_bilingual_text(
                    response.get("description"),
                    "specs/cortex-api.yaml.paths"
                    f"[{path_name!r}].{method_name}.responses[{status_code!r}].description",
                )

    components = _mapping(document.get("components"), "specs/cortex-api.yaml.components")
    schemas = _mapping(components.get("schemas"), "specs/cortex-api.yaml.components.schemas")
    _expect(
        len(schemas) >= 10,
        "specs/cortex-api.yaml.components.schemas must declare the published contract models.",
    )


def _validate_compose() -> None:
    document = _mapping(_load_yaml("compose.local.yaml"), "compose.local.yaml")
    services = _mapping(document.get("services"), "compose.local.yaml.services")
    required_services = {
        "postgres",
        "minio",
        "redis",
        "jaeger-all-in-one",
        "otel-collector",
        "prometheus",
        "grafana",
    }
    missing = sorted(required_services.difference(services))
    _expect(not missing, f"compose.local.yaml.services is missing required services: {missing}.")


def _validate_otel_collector() -> None:
    document = _mapping(_load_yaml("otel-collector.yaml"), "otel-collector.yaml")
    _mapping(document.get("receivers"), "otel-collector.yaml.receivers")
    _mapping(document.get("processors"), "otel-collector.yaml.processors")
    exporters = _mapping(document.get("exporters"), "otel-collector.yaml.exporters")
    _expect("prometheus" in exporters, "otel-collector.yaml.exporters must include prometheus.")
    _expect("debug" in exporters, "otel-collector.yaml.exporters must include debug.")

    service = _mapping(document.get("service"), "otel-collector.yaml.service")
    pipelines = _mapping(service.get("pipelines"), "otel-collector.yaml.service.pipelines")
    _expect("traces" in pipelines, "otel-collector.yaml.service.pipelines must include traces.")
    _expect("metrics" in pipelines, "otel-collector.yaml.service.pipelines must include metrics.")


def _validate_prometheus() -> None:
    document = _mapping(
        _load_yaml("scripts/dev/prometheus.local.yaml"),
        "scripts/dev/prometheus.local.yaml",
    )
    scrape_configs = document.get("scrape_configs")
    _expect(
        isinstance(scrape_configs, list) and scrape_configs,
        "scripts/dev/prometheus.local.yaml.scrape_configs must be a non-empty list.",
    )


def _validate_github_workflow() -> None:
    document = _mapping(_load_yaml(".github/workflows/ci.yaml"), ".github/workflows/ci.yaml")
    _string(document.get("name"), ".github/workflows/ci.yaml.name")

    trigger_value = document.get("on")
    if trigger_value is None and True in document:
        trigger_value = document.get(True)
    trigger = _mapping(trigger_value, ".github/workflows/ci.yaml.on")
    workflow_dispatch = _mapping(
        trigger.get("workflow_dispatch"),
        ".github/workflows/ci.yaml.on.workflow_dispatch",
    )
    inputs = _mapping(
        workflow_dispatch.get("inputs"),
        ".github/workflows/ci.yaml.on.workflow_dispatch.inputs",
    )
    run_runtime_stack = _mapping(
        inputs.get("run_runtime_stack"),
        ".github/workflows/ci.yaml.on.workflow_dispatch.inputs.run_runtime_stack",
    )
    _string(
        run_runtime_stack.get("description"),
        ".github/workflows/ci.yaml.on.workflow_dispatch.inputs.run_runtime_stack.description",
    )
    _expect(
        run_runtime_stack.get("type") == "boolean",
        ".github/workflows/ci.yaml.on.workflow_dispatch.inputs.run_runtime_stack.type"
        " must equal 'boolean'.",
    )

    jobs = _mapping(document.get("jobs"), ".github/workflows/ci.yaml.jobs")
    quality = _mapping(jobs.get("quality"), ".github/workflows/ci.yaml.jobs.quality")
    runtime_stack = _mapping(
        jobs.get("runtime-stack"),
        ".github/workflows/ci.yaml.jobs.runtime-stack",
    )

    quality_steps = quality.get("steps")
    _expect(
        isinstance(quality_steps, list) and quality_steps,
        ".github/workflows/ci.yaml.jobs.quality.steps must be a non-empty list.",
    )
    quality_commands = {
        _string(
            _mapping(step, ".github/workflows/ci.yaml.jobs.quality.steps[*]").get("run"),
            ".github/workflows/ci.yaml.jobs.quality.steps[*].run",
        )
        for step in quality_steps
        if isinstance(step, Mapping) and "run" in step
    }
    _expect(
        "uv sync --all-packages --all-groups --frozen" in quality_commands,
        "The quality workflow must sync the full uv workspace.",
    )
    _expect(
        "uv run --all-packages --all-groups python scripts/ci/check.py" in quality_commands,
        "The quality workflow must invoke scripts/ci/check.py.",
    )

    runtime_steps = runtime_stack.get("steps")
    _expect(
        isinstance(runtime_steps, list) and runtime_steps,
        ".github/workflows/ci.yaml.jobs.runtime-stack.steps must be a non-empty list.",
    )
    runtime_commands = {
        _string(
            _mapping(step, ".github/workflows/ci.yaml.jobs.runtime-stack.steps[*]").get("run"),
            ".github/workflows/ci.yaml.jobs.runtime-stack.steps[*].run",
        )
        for step in runtime_steps
        if isinstance(step, Mapping) and "run" in step
    }
    _expect(
        any(
            "docker compose -p cortex-ci -f compose.local.yaml up -d" in command
            for command in runtime_commands
        ),
        "The runtime-stack workflow must start compose.local.yaml.",
    )
    _expect(
        "uv run --all-packages --all-groups python scripts/ci/wait_for_runtime_stack.py"
        in runtime_commands,
        "The runtime-stack workflow must wait for the stack.",
    )


def _validate_grafana_datasources() -> None:
    document = _mapping(
        _load_yaml("scripts/dev/grafana/datasources/datasources.yaml"),
        "scripts/dev/grafana/datasources/datasources.yaml",
    )
    datasources = document.get("datasources")
    _expect(
        isinstance(datasources, list) and datasources,
        "scripts/dev/grafana/datasources/datasources.yaml.datasources must be a non-empty list.",
    )
    data_source_types = {
        _string(
            _mapping(item, "grafana.datasource").get("type"),
            "grafana.datasource.type",
        )
        for item in datasources
    }
    _expect("prometheus" in data_source_types, "Grafana datasources must include Prometheus.")
    _expect("jaeger" in data_source_types, "Grafana datasources must include Jaeger.")


def _validate_parse_profile() -> None:
    document = _mapping(
        _load_yaml("packages/parse/src/cortex_parse/profiles/auto_default.yaml"),
        "packages/parse/src/cortex_parse/profiles/auto_default.yaml",
    )
    _string(
        document.get("profile_ref"),
        "packages/parse/src/cortex_parse/profiles/auto_default.yaml.profile_ref",
    )
    _string(
        document.get("display_name"),
        "packages/parse/src/cortex_parse/profiles/auto_default.yaml.display_name",
    )
    _string(
        document.get("routing_mode"),
        "packages/parse/src/cortex_parse/profiles/auto_default.yaml.routing_mode",
    )
    _string_list(
        document.get("allowed_engines"),
        "packages/parse/src/cortex_parse/profiles/auto_default.yaml.allowed_engines",
    )
    _mapping(
        document.get("normalization_defaults"),
        "packages/parse/src/cortex_parse/profiles/auto_default.yaml.normalization_defaults",
    )
    _mapping(
        document.get("fallback_policy"),
        "packages/parse/src/cortex_parse/profiles/auto_default.yaml.fallback_policy",
    )


def main() -> int:
    validators = [
        ("OpenAPI contract", _validate_openapi),
        ("compose stack", _validate_compose),
        ("OTel collector config", _validate_otel_collector),
        ("Prometheus config", _validate_prometheus),
        ("GitHub workflow", _validate_github_workflow),
        ("Grafana datasources", _validate_grafana_datasources),
        ("parse profile", _validate_parse_profile),
    ]

    for label, validator in validators:
        validator()
        print(f"[cortex] validated {label}.")

    print("[cortex] YAML/OpenAPI validation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
