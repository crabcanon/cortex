"""Knowledge runtime bootstrap helpers."""

from cortex_common import CogneeSettings

from .runtime import build_cognee_runtime
from .service import KnowledgeDatasetService


def build_knowledge_service(settings: CogneeSettings) -> KnowledgeDatasetService:
    """Build the default knowledge runtime for the API process."""
    return KnowledgeDatasetService(build_cognee_runtime(settings))
