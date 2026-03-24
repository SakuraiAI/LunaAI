from dataclasses import dataclass, field


@dataclass(slots=True)
class ShortMemory:
    items: list[str] = field(default_factory=list)
    limit: int = 10

    def add(self, value: str) -> None:
        self.items.append(value)
        if len(self.items) > self.limit:
            self.items = self.items[-self.limit :]
