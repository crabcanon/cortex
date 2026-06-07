with open("packages/knowledge/src/cortex_knowledge/runtime.py", "r") as f:
    content = f.read()

new_content = content.replace(
"""    if not enabled:
        return DisabledCogneeRuntime(reason="Cognee runtime is disabled by configuration.")
    runtime = PythonCogneeRuntime(config=_resolved_cognee_config(loaded_runtime))
    if runtime.descriptor.status != "active":
        return DisabledCogneeRuntime(
            reason=runtime.descriptor.reason or "Cognee runtime module is unavailable."
        )
    return runtime""",
"""    if not enabled:
        return DisabledCogneeRuntime(reason="Cognee runtime is disabled by configuration.")
    if not _cognee_available():
        return DisabledCogneeRuntime(reason="Cognee runtime module is unavailable.")
    runtime = PythonCogneeRuntime(config=_resolved_cognee_config(loaded_runtime))
    if runtime.descriptor.status != "active":
        return DisabledCogneeRuntime(
            reason=runtime.descriptor.reason or "Cognee runtime module is unavailable."
        )
    return runtime""")

with open("packages/knowledge/src/cortex_knowledge/runtime.py", "w") as f:
    f.write(new_content)
