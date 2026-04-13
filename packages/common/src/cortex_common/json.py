"""JSON helper functions."""

import json
from typing import Any


def json_dumps(value: Any) -> str:
    """Serialize a Python value to a deterministic JSON string."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def json_loads(payload: str) -> Any:
    """Deserialize a JSON string."""
    return json.loads(payload)
