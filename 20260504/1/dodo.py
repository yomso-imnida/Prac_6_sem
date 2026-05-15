"""Задачи DoIt для сборки переводов, документации и тестов."""

import shutil
from pathlib import Path


# по умолчанию команда doit будет собирать html-документацию
DOIT_CONFIG = {
    "default_tasks": ["html"],
}

# настройки gettext / babel: домен перевода и используемая локаль
TEXT_DOMAIN = "mood"
LOCALE = "ru_RU.UTF-8"

# Пути к файлам перевода:
# pot - шаблон со строками из исходного кода
# po  - текстовый файл русского перевода
# mo  - скомпилированный файл, который использует gettext

PO_DIR = Path("mood/server/po")
POT_FILE = PO_DIR / f"{TEXT_DOMAIN}.pot"
PO_FILE = PO_DIR / LOCALE / "LC_MESSAGES" / f"{TEXT_DOMAIN}.po"
MO_FILE = PO_DIR / LOCALE / "LC_MESSAGES" / f"{TEXT_DOMAIN}.mo"

# пути к исходникам и результатам сборки Sphinx-документации
DOC_DIR = Path("doc")
DOC_BUILD_DIR = DOC_DIR / "_build"
HTML_INDEX = DOC_BUILD_DIR / "html" / "index.html"


def clean_targets(targets):
    """Удаление файлов, перечисленных в targets задачи DoIt."""
    for target in targets:
        Path(target).unlink(missing_ok=True)


def python_files():
    """Получение всех файлов MUD-а на python-е."""
    return list(Path("mood").rglob("*.py"))


def rst_files():
    """Получение исходных файлов Sphinx-документации."""
    return list(DOC_DIR.rglob("*.rst")) + [DOC_DIR / "conf.py"]


def task_pot():
    """Создание шаблона перевода (mood.pot) из исходного кода."""
    return {
        # pybabel extract ищет строки, обернутые в gettext/ngettext
        "actions": [
            f"pybabel extract -o {POT_FILE} mood",
        ],

        "file_dep": python_files(),         # если меняется исходный код, шаблон перевода нужно обновить
        "targets": [POT_FILE],              # целевой файл нужен, чтобы doit не пересобирал задачу без причины
        "clean": [clean_targets],           # clean_targets удаляет файлы, перечисленные в targets
    }


def task_po():
    """Обновление русского файла перевода (mood.po) по шаблону mood.pot."""
    return {
        # pybabel update переносит новые строки из .pot в существующий .po
        "actions": [
            f"pybabel update -D {TEXT_DOMAIN} -d {PO_DIR} "
            f"-l {LOCALE} -i {POT_FILE}",
        ],

        # .po зависит от шаблона .pot
        "file_dep": [POT_FILE],
        "targets": [PO_FILE],
    }


def task_mo():
    """Компилирование файла с русским переводом (из mood.po в mood.mo)."""
    return {
        # pybabel compile создаёт бинарный .mo-файл для gettext
        "actions": [
            f"pybabel compile -D {TEXT_DOMAIN} -d {PO_DIR} "
            f"-l {LOCALE} -i {PO_FILE}",
        ],

        # .mo пересобирается, если изменился .po
        "file_dep": [PO_FILE],
        "targets": [MO_FILE],
        "clean": [clean_targets],
    }


def task_i18n():
    """Полная сборка файлов перевода: шаблон, .po-файл и .mo-файл."""
    return {
        "actions": [],
        "task_dep": ["pot", "po", "mo"],
    }


def task_html():
    """Сборка HTML-документации."""
    return {
        # sphinx-build -M html собирает HTML в doc/_build/html
        "actions": [
            f"sphinx-build -M html {DOC_DIR} {DOC_BUILD_DIR}",
        ],

        # документация зависит от .rst, conf.py и python-кода для autodoc
        "file_dep": rst_files() + python_files(),
        "targets": [HTML_INDEX],

        # каталог сборки удаляется целиком, поэтому используется shutil.rmtree
        "clean": [
            (shutil.rmtree, [DOC_BUILD_DIR], {"ignore_errors": True}),
        ],
    }


def task_test():
    """Запуск клиент-серверных тестов после сборки перевода."""
    return {
        # тесты проверяют работу клиента и сервера через unittest
        "actions": [
            "python -m unittest test_server_from_client",
        ],

        # тесты зависят от кода игры и от файла с тестами
        "file_dep": python_files() + [Path("test_server_from_client.py")],

        # сначала собирается перевод, т.к. тестируются русскоязыычные ответы
        "task_dep": ["i18n"],
    }
