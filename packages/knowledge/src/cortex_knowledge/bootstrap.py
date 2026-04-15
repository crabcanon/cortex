"""Knowledge runtime bootstrap helpers."""

from cortex_common import CogneeSettings, LoadedRuntimeConfig, load_runtime_config

from .runtime import build_cognee_runtime
from .service import KnowledgeDatasetService


def build_knowledge_service(
    settings: CogneeSettings,
    runtime_config: LoadedRuntimeConfig | None = None,
) -> KnowledgeDatasetService:
    """Build the default knowledge runtime for the API process."""
    loaded_runtime = runtime_config or load_runtime_config()
    return KnowledgeDatasetService(build_cognee_runtime(settings, loaded_runtime))
