from dataclasses import dataclass, field
from pathlib import Path

from freight_check.contracts import ExtractedField


@dataclass(slots=True, frozen=True)
class RawDocument:
    """Сырые извлеченные данные из документа.

    Содержит все текстовые блоки с координатами, но без семантической привязки.
    Передается в модуль семантического извлечения.
    """
    file_path: Path
    pages: list[list[ExtractedField]]  # Сетка ячеек/блоков: [страница][ячейка]
    document_type: str = "unknown"  # "xlsx", "xml", "pdf", "scan" и т.д.
    metadata: dict = field(default_factory=dict)  # Доп. информация (кол-во листов и т.п.)