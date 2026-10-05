from dataclasses import dataclass, field


class ConversionError(ValueError):
    def __init__(self, message, line=1, attribute=None):
        super().__init__(message)
        self.errors = [
            {
                "line": line,
                "message": message,
                "attribute": attribute,
                "severity": "fatal",
            }
        ]


@dataclass
class Attribute:
    name: str
    type: str
    values: list[str] = field(default_factory=list)
    date_format: str | None = None


@dataclass
class Dataset:
    relation: str
    attributes: list[Attribute]
    rows: list[list[str | None]]
    lines: list[int]
