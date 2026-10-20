# «Рейс-Проверка»

Автономная десктоп-утилита для локальной кросс-валидации транспортных документов.

---

## Стек технологий

* **Среда выполнения:** Python 3.13.
* **Интерфейс:** `PySide6`.
* **Парсеры:** `openpyxl`, `xlrd`, `python-docx`, `pdfplumber`, `pypdfium2`, `xml.etree.ElementTree`.
* **OCR и графика:** `rapidocr-onnxruntime`, `opencv-python-headless`, `Pillow`.
* **Сверка и нормализация:** `rapidfuzz`.
* **Контроль качества:** `ruff`, `basedpyright`, `pytest`, `pre-commit`.
* **Дистрибуция:** `PyInstaller`, `Inno Setup`.

---

## Быстрый старт

### Требования
* Установленный Python 3.13
* Установленный менеджер пакетов [`uv`](https://github.com/astral-sh/uv)

### Настройка локального окружения

```bash
# 1. Клонирование репозитория
git clone <repo-url>
cd freight-check

# 2. Установка зависимостей и синхронизация окружения
uv sync

# 3. Активация pre-commit хуков (ruff, basedpyright, pytest)
uv run pre-commit install
```

---

## Структура проекта

```text
freight-check/
├── assets/
│   ├── models/                # Локальные веса ONNX
│   └── styles/                # Таблицы стилей интерфейса
├── src/
│   └── freight_check/
│       ├── contracts.py       # Dataclass-модели обмена
│       ├── ui/                # PySide6 виджеты, QThread worker
│       ├── parsers/           # Прямое чтение файлов и конвейер OCR
│       └── core/              # Семантика, нормализация и сопоставление
├── tests/                     # Модульные и интеграционные тесты
├── .pre-commit-config.yaml    # Автоматизация проверок перед коммитом
├── pyproject.toml             # Конфигурация uv, ruff, basedpyright, pytest
└── README.md
```

---

## Команды разработки и контроля качества

Все инструменты запускаются через `uv run`:

```bash
# Проверка и автоисправление стиля (Ruff)
uv run ruff check --fix
uv run ruff format

# Статическая проверка типов
uv run basedpyright

# Запуск тестов
uv run pytest

# Ручной прогон всех pre-commit хуков
uv run pre-commit run --all-files
```

---

## Регламент работы с Git

1. Прямые коммиты в ветку `main` запрещены.
2. Вся разработка ведется в ветках `feature/<название>` или `bugfix/<название>`.
3. Слияние в `main` происходит через Pull Request после прохождения CI и минимум одного код-ревью.

### Формат сообщений коммитов (Conventional Commits)

```text
<тип>(<область>): <описание с маленькой буквы в повелительном наклонении>
```

**Типы:** `feat`, `fix`, `test`, `refactor`, `perf`, `chore`, `ci`, `docs`.

**Области (`scope`):**
* `contracts` — модели данных
* `ui` — экраны и стили PySide6
* `parsers` — чтение документов
* `ocr` — графический конвейер
* `extract` — привязка якорных слов и извлечение полей
* `norm` — нормализация
* `matcher` — правила сопоставления и весовой баланс
* `pack` — сборка приложения

*Примеры:*
* `feat(ui): добавить таблицу расхождений с цветовой индикацией`
* `feat(parsers): добавить извлечение таблиц через openpyxl`
* `fix(norm): исправить парсинг дробного веса с разделителем-запятой`
