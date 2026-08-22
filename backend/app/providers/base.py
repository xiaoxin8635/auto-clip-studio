from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..schemas import ProviderResult


class ProviderError(RuntimeError):
    pass


class AIProvider(ABC):
    @abstractmethod
    async def analyze(self, media_path: Path, duration_ms: int) -> ProviderResult:
        """Return a validated transcript and bounded candidate segments."""
