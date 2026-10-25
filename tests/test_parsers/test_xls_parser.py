import pytest
from pathlib import Path
from freight_check.parsers.xls_parser import XLSParser


def test_parse_xls_not_found() -> None:
    parser = XLSParser()
    with pytest.raises(FileNotFoundError):
        parser.parse(Path("missing.xls"))


def test_parse_invalid_xls(tmp_path: Path) -> None:
    """Тест обработки файла, который не является валидным XLS."""
    file_path = tmp_path / "fake.xls"
    file_path.write_text("Это просто текст, а не бинарный XLS", encoding="utf-8")

    parser = XLSParser()
    # xlrd должен выбросить XLRDError, который мы мапим в ValueError
    with pytest.raises(ValueError, match="Ошибка парсинга XLS"):
        parser.parse(file_path)