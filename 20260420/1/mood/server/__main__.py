"""Запуск MUD-а."""

import asyncio
import gettext
from pathlib import Path

from mood.common.constants import (
    DEFAULT_LOCALE,
    HOST,
    LOCALE_DIR,
    MONSTER_MOVE_INTERVAL,
    MSG_DELIM,
    PORT,
    RU_LOCALE,
    TEXT_DOMAIN,
)
from mood.server.game import GameParam, make_cowsay_message


# объект, хранящий текущее состояние
game = GameParam()

# {username: {"writer": writer, "locale": ..., "translation": ...}} - подключенные пользователи
# ключ - имя пользователя, значение - writer, выбранная локаль и объект gettext-перевода
clients = {}


def get_translation(locale_name):
    """Получение перевода для локали клиента."""
    # если перевода нет -> оставляем исходный (английский)
    if locale_name not in (RU_LOCALE, "ru_RU.UTF-8", "ru_RU"):
        return gettext.NullTranslations()

    # переводы лежат внутри серверного модуля: mood/server/po
    locale_dir = Path(__file__).resolve().parent / LOCALE_DIR

    return gettext.translation(
        TEXT_DOMAIN,
        localedir=str(locale_dir),
        languages=["ru_RU.UTF-8", "ru_RU.UTF8", "ru_RU", "ru"],
        fallback=True,
    )


def get_client_translation(username):
    """Получение объекта перевода для конкретного клиента."""
    client = clients.get(username)

    if client is None:
        return gettext.NullTranslations()

    return client["translation"]


def translate_for(username):
    """Получение функций gettext и ngettext для конкретного клиента."""
    translation = get_client_translation(username)
    return translation.gettext, translation.ngettext


def hp_text(n, ngettext):
    """Форматирование очков здоровья с правильной формой множественного числа."""
    return ngettext("{} hp", "{} hp", n).format(n)


async def send_event_to_everyone(event, except_username=None, **kwargs):
    """Отправка события всем клиентам с учётом локали каждого клиента."""
    dead_clients = []                           # клиенты, которым не удалось отправить сообщение
    current_clients = list(clients.items())     # копия клиентов на момент рассылки

    for username, client in current_clients:
        if username == except_username:
            continue

        writer = client["writer"]                   # поток записи конкретного пользователя
        _, ngettext = translate_for(username)       # для каждого получателя берем его функцию множественного числа

        # сообщение собирается отдельно под локаль конкретного получателя
        message = make_event_message(event, username, ngettext, **kwargs)

        try:
            writer.write((message + MSG_DELIM).encode())
        except Exception:
            dead_clients.append(username)

    for username, client in current_clients:
        if username == except_username or username in dead_clients:
            continue

        try:
            await client["writer"].drain()
        except Exception:
            dead_clients.append(username)

    # удаляем мертвых пользователей
    for username in dead_clients:
        clients.pop(username, None)


def make_event_message(event, receiver, ngettext, **kwargs):
    """Формирование локализованного сообщения о событии."""
    _ = translate_for(receiver)[0]          # gettext-функция выбирается по локали получателя сообщения

    match event:
        case "join":
            return _("{} joined the MUD").format(kwargs["username"])

        case "left":
            return _("{} left the MUD").format(kwargs["username"])

        case "addmon":
            message = _("{} added monster {} to ({}, {}) with {}").format(
                kwargs["username"],
                kwargs["name"],
                kwargs["x"],
                kwargs["y"],
                hp_text(kwargs["hp"], ngettext),
            )

            if kwargs["replaced"]:
                message += "\n" + _("Replaced the old monster")

            return message

        case "attack_died":
            return _("{} attacked {} with {}, damage {}, {} died").format(
                kwargs["username"],
                kwargs["name"],
                kwargs["weapon"],
                hp_text(kwargs["damage"], ngettext),
                kwargs["name"],
            )

        case "attack_alive":
            return _("{} attacked {} with {}, damage {}, {} now has {}").format(
                kwargs["username"],
                kwargs["name"],
                kwargs["weapon"],
                hp_text(kwargs["damage"], ngettext),
                kwargs["name"],
                hp_text(kwargs["hp_left"], ngettext),
            )

        case "monster_moved":
            return _("{} moved one cell {}").format(
                kwargs["name"],
                kwargs["direction"],
            )

        case _:
            return ""


async def send_to_one(writer, message):
    """Отправка сообщения одному пользователю."""
    # в конец добавляем MSG_DELIM, чтобы клиент понял границу сообщения
    writer.write((message + MSG_DELIM).encode())

    # ждем, пока данные из буфера уйдут в сокет
    await writer.drain()                            # await - приостановка


async def send_to_everyone(message, except_username=None):
    """Отправка сообщения всем пользователям (широковещательное сообщение)."""
    dead_clients = []                           # имена пользователей, которые по какой-то причине отключились
    current_clients = list(clients.items())     # копия списка клиентов на момент рассылки

    # кидаем сообщение всем подключенным пользователям
    for username, client in current_clients:
        if username == except_username:
            continue

        # поток записи конкретного клиента
        writer = client["writer"]

        try:
            writer.write((message + MSG_DELIM).encode())        # байт-строка отправляется в сокет
        except Exception:
            dead_clients.append(username)

    # ожидаем доотправки сообщений в сокеты
    for username, client in current_clients:
        if username == except_username or username in dead_clients:
            continue

        writer = client["writer"]

        try:
            await writer.drain()
        except Exception:
            dead_clients.append(username)

    # удаляем мертвых пользователей
    for username in dead_clients:
        clients.pop(username, None)


async def send_encounter(username, encounter):
    """Отправка сообщения о встрече с монстром (одному из игроков)."""
    client = clients.get(username)          # encounter отправляется только одному игроку, а не всем

    if client is None:
        return

    await send_to_one(client["writer"], make_cowsay_message(encounter))


async def move_monsters_periodically():
    """Перемещение одного случайного монстра через фиксированный промежуток времени."""
    while True:
        # первый ход происходит только после ожидания
        await asyncio.sleep(MONSTER_MOVE_INTERVAL)

        # запрещено движение монстров при off
        if not game.moving_monsters:
            continue

        # выбираем случайного монстра и пробуем переместить его
        result = game.move_random_monster()

        # если монстров нет -> ждём следующего интервала
        if result is None:
            continue

        await send_event_to_everyone(
            "monster_moved",
            name=result["name"],
            direction=result["direction"],
        )

        # если монстр пришёл на клетку с игроками -> показываем им encounter
        encounter = result["encounter"]

        if encounter is None:
            continue

        # encounter отправляется только тем игрокам, которые стоят на новой клетке монстра
        for username in result["players"]:
            await send_encounter(username, encounter)


async def client_processing(reader, writer):
    """Обработка одного клиентского подключения."""
    '''
    Клиент: сначала присылает имя пользователя, затем строки с командами
    Сервер:
        1. читает имя и проверяет, свободно ли оно
        2. запоминает игрока
        3. читает команды этого игрока
        4. обрабатывает их
        5. рассылает личные или широковещательные сообщения
        6. при отключении удаляет игрока и сообщает остальным о его уходе
    '''

    username = None             # имя появится после 1-го сообщения от клиента

    try:
        # первое сообщение от клиента - имя пользователя
        data = await reader.readline()
        if not data:
            writer.close()
            await writer.wait_closed()
            return

        # имя должно быть непустым, без пробелов и уникальным
        username = data.decode().strip()

        if (not username) or (" " in username):
            await send_to_one(writer, "Invalid username")
            writer.close()
            await writer.wait_closed()
            return

        if username in clients:
            await send_to_one(writer, f"Username {username} is already taken")
            writer.close()
            await writer.wait_closed()
            return

        # регистрируем подключение, создаём игрока
        clients[username] = {
            "writer": writer,
            "locale": DEFAULT_LOCALE,
            "translation": get_translation(DEFAULT_LOCALE),
        }
        game.add_player(username)

        await send_to_one(writer, f"Welcome, {username}")
        await send_event_to_everyone("join", except_username=username, username=username)

        # дальше клиент присылает игровые команды
        while (data := await reader.readline()):
            cmd = data.decode().strip()

            if not cmd:
                continue

            res = game.process_command(username, cmd)

            match res["status"]:
                case "move":
                    x, y, encounter = res["data"]
                    await send_to_one(writer, f"Moved to ({x}, {y})")
                    if encounter is not None:
                        await send_to_one(writer, make_cowsay_message(encounter))

                case "addmon":
                    await send_event_to_everyone(
                        "addmon",
                        username=username,
                        name=res["name"],
                        x=res["x"],
                        y=res["y"],
                        hp=res["hp"],
                        replaced=res["replaced"],
                    )

                case "no_monster":
                    if res["name"] is None:
                        await send_to_one(writer, "No monster here")
                    else:
                        await send_to_one(writer, f"No {res['name']} here")

                case "attack":
                    if res["died"]:
                        await send_event_to_everyone(
                            "attack_died",
                            username=username,
                            name=res["name"],
                            weapon=res["weapon"],
                            damage=res["damage"],
                        )
                    else:
                        await send_event_to_everyone(
                            "attack_alive",
                            username=username,
                            name=res["name"],
                            weapon=res["weapon"],
                            damage=res["damage"],
                            hp_left=res["hp_left"],
                        )

                case "sayall":
                    await send_to_everyone(f"{username}: {res['message']}")

                case "movemonsters":
                    state = "on" if res["enabled"] else "off"

                    await send_to_one(writer, f"Moving monsters: {state}")

                case "locale":
                    # локаль хранится отдельно для каждого пользователя
                    clients[username]["locale"] = res["locale"]
                    clients[username]["translation"] = get_translation(res["locale"])

                    # ответ об установке локали отправляется только этому клиенту
                    _ = clients[username]["translation"].gettext
                    await send_to_one(writer, _("Set up locale: {}").format(res["locale"]))

                case "error":
                    await send_to_one(writer, res["message"])

    # при любом завершении соединения удаляем игрока и рассылаем сообщение о выходе
    finally:
        # проверув: был ли клиент полностью зарегистрирован в игре
        was_connected = (username is not None) and (username in clients)

        if username is not None:
            clients.pop(username, None)
            game.remove_player(username)

            if was_connected:
                await send_event_to_everyone("left", except_username=username, username=username)

        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    """Запуск MUD-сервер."""
    server = await asyncio.start_server(client_processing, HOST, PORT)

    # фоновая задача двигает монстров вне зависимости от команд клиентов
    asyncio.create_task(move_monsters_periodically())

    async with server:
        await server.serve_forever()


def serve():
    """Запуск сервера из командной строки или из тестов."""
    asyncio.run(main())


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        print()
        print("Server stopped")
