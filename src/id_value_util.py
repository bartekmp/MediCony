from dataclasses import dataclass


@dataclass
class IdValue:
    id: int
    value: str | None = None

    def __init__(self, id: int, value: str | None = None):
        self.id = id
        self.value = value


IdsValues = list[IdValue]
