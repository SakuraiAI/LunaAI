from abc import ABC, abstractmethod


class BaseModel(ABC):
    @abstractmethod
    def generate(self, prompt: str | list[dict[str, str]]) -> str:
        raise NotImplementedError
