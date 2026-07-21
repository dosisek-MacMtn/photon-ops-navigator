from abc import ABC, abstractmethod


class NarrativeProvider(ABC):
    @abstractmethod
    async def summarize(self, plan: dict) -> str: ...
