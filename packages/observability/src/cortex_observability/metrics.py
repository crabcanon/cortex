"""Small metric facade."""

from typing import Any

from opentelemetry import metrics


class MetricsFacade:
    """Lazy metric constructor wrapper."""

    def __init__(self, meter_name: str) -> None:
        self._meter = metrics.get_meter(meter_name)
        self._counters: dict[str, Any] = {}
        self._histograms: dict[str, Any] = {}

    def counter(self, name: str, *, unit: str = "1", description: str = "") -> Any:
        if name not in self._counters:
            self._counters[name] = self._meter.create_counter(
                name,
                unit=unit,
                description=description,
            )
        return self._counters[name]

    def histogram(self, name: str, *, unit: str = "1", description: str = "") -> Any:
        if name not in self._histograms:
            self._histograms[name] = self._meter.create_histogram(
                name,
                unit=unit,
                description=description,
            )
        return self._histograms[name]
