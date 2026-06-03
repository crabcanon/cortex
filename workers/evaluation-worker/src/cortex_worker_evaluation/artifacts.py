"""Evaluation worker artifact compatibility exports."""

from cortex_evaluation import (
    EvaluationStorageCaller as WorkerStorageCaller,
    persist_evaluation_report,
)

__all__ = ["WorkerStorageCaller", "persist_evaluation_report"]
