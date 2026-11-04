"""Скрипт оркестрации и автоматизации сборки дистрибутива «Рейс-Проверка».

Цепочка шагов:
1. Синхронизация зависимостей через uv sync.
2. Проверка качества: ruff check, basedpyright, pytest.
3. Сборка переносимого каталога через PyInstaller.
4. Поиск компилятора Inno Setup (ISCC.exe) и сборка инсталлятора Windows.
5. Комплексная проверка целостности выходных артефактов.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tomllib
import winreg
from pathlib import Path

# Обеспечиваем корректный вывод UTF-8 (кириллицы) в консоли Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def log_step(step_num: int, title: str) -> None:
    """Вывод визуального заголовка этапа сборки."""
    print(f"\n{'=' * 72}")
    print(f"[{step_num}/5] {title}")
    print(f"{'=' * 72}")


def run_command(cmd: list[str], description: str) -> None:
    """Запуск внешней команды с проверкой кода возврата."""
    print(f"-> Выполнение: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(
            f"\n[ERROR] Ошибка на этапе '{description}' (код возврата {result.returncode})",
            file=sys.stderr,
        )
        sys.exit(result.returncode)


def get_project_metadata() -> tuple[str, str]:
    """Считывает версию и список авторов из канонического pyproject.toml."""
    pyproject_file = PROJECT_ROOT / "pyproject.toml"
    with open(pyproject_file, "rb") as f:
        data = tomllib.load(f)

    project_info = data.get("project", {})
    version = str(project_info.get("version", "0.1.0"))

    authors_data = project_info.get("authors", [])
    author_names = [a["name"] for a in authors_data if "name" in a]
    publisher = ", ".join(author_names) if author_names else "Freight Check Contributors"

    return version, publisher


def find_iscc_compiler() -> Path | None:
    """Осуществляет поиск компилятора Inno Setup (ISCC.exe) в системе."""
    # 1. Проверка PATH
    which_path = shutil.which("iscc") or shutil.which("iscc.exe") or shutil.which("ISCC")
    if which_path:
        return Path(which_path)

    # 2. Стандартные пути установки Windows
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    program_files = os.environ.get("PROGRAMFILES", r"C:\Program Files")

    candidates = [
        Path(program_files_x86) / "Inno Setup 6" / "ISCC.exe",
        Path(program_files) / "Inno Setup 6" / "ISCC.exe",
        Path(local_app_data) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    # 3. Поиск через реестр Windows (HKLM / HKCU)
    reg_keys = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Inno Setup 6_is1",
        ),
    ]

    for root_key, subkey in reg_keys:
        try:
            with winreg.OpenKey(root_key, subkey) as key:
                install_loc, _ = winreg.QueryValueEx(key, "InstallLocation")
                if install_loc:
                    iscc_path = Path(install_loc) / "ISCC.exe"
                    if iscc_path.exists():
                        return iscc_path
        except OSError:
            continue

    return None


def verify_artifacts(version: str, expect_installer: bool) -> None:
    """Проверяет наличие и целостность собранных артефактов."""
    dist_dir = PROJECT_ROOT / "dist" / "freight-check"
    exe_file = dist_dir / "freight-check.exe"
    internal_dir = dist_dir / "_internal"

    if not exe_file.exists() or exe_file.stat().st_size < 100_000:
        print(f"[ERROR] Бинарный файл {exe_file} не найден или поврежден!", file=sys.stderr)
        sys.exit(1)

    # Проверка ключевых ассетов
    qss_file = internal_dir / "assets" / "styles" / "style.qss"
    icon_file = internal_dir / "assets" / "icons" / "app_icon.ico"
    if not qss_file.exists():
        print(f"[ERROR] Таблица стилей {qss_file} не найдена в _internal!", file=sys.stderr)
        sys.exit(1)
    if not icon_file.exists():
        print(f"[ERROR] Иконка {icon_file} не найдена в _internal!", file=sys.stderr)
        sys.exit(1)

    # Проверка моделей OCR
    models_dir = internal_dir / "rapidocr_onnxruntime" / "models"
    onnx_models = list(models_dir.glob("*.onnx")) if models_dir.exists() else []
    if len(onnx_models) < 3:
        print(
            f"[ERROR] В каталоге моделей {models_dir} найдено только {len(onnx_models)} .onnx файлов (ожидалось 3)!",
            file=sys.stderr,
        )
        sys.exit(1)

    total_dist_bytes = sum(f.stat().st_size for f in dist_dir.rglob("*") if f.is_file())
    print(f"\n[OK] Каталог переносимого приложения: {dist_dir}")
    print(f"     Размер каталога: {total_dist_bytes / (1024 * 1024):.2f} МБ")
    print(f"     Главный бинарник: {exe_file} ({exe_file.stat().st_size / (1024 * 1024):.2f} МБ)")
    print(f"     Моделей OCR в комплекте: {len(onnx_models)}")

    if expect_installer:
        installer_dir = PROJECT_ROOT / "dist_installer"
        installer_file = installer_dir / f"freight-check-setup-v{version}-x64.exe"
        if not installer_file.exists() or installer_file.stat().st_size < 1_000_000:
            print(
                f"[ERROR] Инсталлятор {installer_file} не найден или имеет некорректный размер!",
                file=sys.stderr,
            )
            sys.exit(1)
        print(f"[OK] Установочный пакет Inno Setup: {installer_file}")
        print(f"     Размер инсталлятора: {installer_file.stat().st_size / (1024 * 1024):.2f} МБ")


def main() -> None:
    """Точка входа скрипта сборки."""
    parser = argparse.ArgumentParser(description="Сборка дистрибутива «Рейс-Проверка»")
    parser.add_argument(
        "--skip-tests", action="store_true", help="Пропустить проверки linter и pytest"
    )
    parser.add_argument(
        "--no-installer",
        action="store_true",
        help="Собрать только каталог PyInstaller без Inno Setup",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Предварительно очистить каталоги build/, dist/ и dist_installer/",
    )
    args = parser.parse_args()

    version, publisher = get_project_metadata()
    print(f"Сборка дистрибутива «Рейс-Проверка» v{version}")
    print(f"Издатели: {publisher}")

    if args.clean:
        for folder in ("build", "dist", "dist_installer"):
            path = PROJECT_ROOT / folder
            if path.exists():
                print(f"Очистка каталога {path}...")
                shutil.rmtree(path, ignore_errors=True)

    # Шаг 1: Синхронизация зависимостей
    log_step(1, "Синхронизация зависимостей виртуального окружения (uv sync)")
    run_command(["uv", "sync"], "Синхронизация окружения uv")

    # Шаг 2: Проверка качества
    log_step(2, "Контроль качества кодовой базы")
    if args.skip_tests:
        print("Пропуск проверок качества (--skip-tests).")
    else:
        run_command(["uv", "run", "ruff", "check"], "Линтинг кода через Ruff")
        run_command(["uv", "run", "basedpyright"], "Статическая проверка типов basedpyright")
        run_command(["uv", "run", "pytest"], "Запуск набора тестов pytest")
        print("[OK] Все тесты и статические анализаторы завершились успешно.")

    # Шаг 3: Сборка каталога через PyInstaller
    log_step(3, "Сборка переносимого каталога через PyInstaller")
    spec_file = PROJECT_ROOT / "freight_check.spec"
    run_command(
        ["uv", "run", "pyinstaller", str(spec_file), "--clean", "-y"],
        "Сборка PyInstaller",
    )

    # Шаг 4: Сборка инсталлятора Inno Setup
    log_step(4, "Компиляция инсталлятора Inno Setup")
    installer_built = False
    if args.no_installer:
        print("Сборка инсталлятора пропущена пользователем (--no-installer).")
    else:
        iscc = find_iscc_compiler()
        if iscc is None:
            print(
                "\n[WARNING] Компилятор Inno Setup (ISCC.exe) не обнаружен в системе.\n"
                "Сборка установщика пропущена. Портативный каталог в 'dist/freight-check' готов к использованию.\n"
                "Для локальной сборки инсталлятора установите Inno Setup:\n"
                "  winget install JRSoftware.InnoSetup\n"
                "  или choco install innosetup\n"
            )
        else:
            print(f"Найден компилятор Inno Setup: {iscc}")
            iss_script = PROJECT_ROOT / "installer.iss"
            run_command(
                [
                    str(iscc),
                    f"/DMyAppVersion={version}",
                    f"/DMyAppPublisher={publisher}",
                    str(iss_script),
                ],
                "Компиляция инсталлятора Inno Setup",
            )
            installer_built = True

    # Шаг 5: Проверка целостности выходных артефактов
    log_step(5, "Валидация целостности собранных артефактов")
    verify_artifacts(version=version, expect_installer=installer_built)

    print("\n" + "#" * 72)
    print(" СБОРКА УСПЕШНО ЗАВЕРШЕНА!")
    print("#" * 72 + "\n")


if __name__ == "__main__":
    main()
