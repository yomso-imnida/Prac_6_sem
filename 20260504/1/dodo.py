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

# временная директория внутри пакета; в нее копируется HTML-документация перед сборкой wheel
PACKAGE_DOC_DIR = Path("mood") / "doc_html"


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


def copy_html_to_package():
    """Копирование HTML-документации внутрь пакета (для wheel)."""
    # удаляем старую копию документации
    if PACKAGE_DOC_DIR.exists():
        shutil.rmtree(PACKAGE_DOC_DIR)

    # копируем уже собранную HTML-документацию в пакет mood
    shutil.copytree(DOC_BUILD_DIR / "html", PACKAGE_DOC_DIR)


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


def task_packagedoc():
    """Копирование собранной HTML-документации внутрь пакета."""
    return {
        "actions": [copy_html_to_package],      # копирование
        "task_dep": ["html"],                   # сборка HTML-документации

        # файл в документации, по которому doit понимает, что копирование уже сделано
        "targets": [PACKAGE_DOC_DIR / "index.html"],

        # удаление временной копии документации
        "clean": [
            (shutil.rmtree, [PACKAGE_DOC_DIR], {"ignore_errors": True}),
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


def task_sdist():
    """Сборка дистрибутива исходников."""
    return {
        # собираем архив исходников (.tar.gz)
        "actions": [
            "python -m build --sdist",
        ],

        # если что-то изменилось (исходники, документация, перевод, настройки сборки) ->
        # -> собираем sdist заново
        "file_dep": python_files()
        + rst_files()
        + [
            Path("pyproject.toml"),
            Path("MANIFEST.in"),
            PO_FILE,
            POT_FILE,
            Path("mood/server/data/jgsbat.txt"),
        ],

        # не фиксируем имя target, т.к. оно зависит от версии пакета
        "targets": [],
    }


def task_wheel():
    """Сборка wheel-дистрибутива (для установки)."""
    return {
        # собираем wheel; это готовый пакет для установки через pip
        "actions": [
            "python -m build --wheel",
        ],

        # wheel должен включать в себя готовый перевод и HTML-документацию
        "task_dep": ["i18n", "packagedoc"],

        # если что-то изменилось (исходники, документация, перевод, настройки сборки) ->
        # -> собираем wheel заново
        "file_dep": python_files()
        + [
            Path("pyproject.toml"),
            MO_FILE,
            Path("mood/server/data/jgsbat.txt"),
            PACKAGE_DOC_DIR / "index.html",
        ],

        # не фиксируем имя target, т.к. оно зависит от версии пакета
        "targets": [],
    }
