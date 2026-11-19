from __future__ import annotations

import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from scripts.dataset_generator import generate_synthetic_dataset


def main() -> None:
    """Точка входа генерации синтетического набора документов."""
    project_root = Path(__file__).resolve().parents[2]
    output_dir = project_root / "tests" / "fixtures" / "synthetic_dataset"
    print(f"Генерация синтетического набора документов в: {output_dir}")
    manifest = generate_synthetic_dataset(output_dir)
    total_pairs = sum(len(s["pairs"]) for s in manifest.get("scenarios", {}).values())
    print(f"Успешно создано пар: {total_pairs} (30 файлов)")
    print(f"Манифест: {output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
