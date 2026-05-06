"""Запуск MUD-а."""

import asyncio

from mood.common.constants import HOST, MSG_DELIM, PORT, MONSTER_MOVE_INTERVAL
from mood.server.game import GameParam, make_cowsay_message


# объект, хранящий текущее состояние
game = GameParam()
clients = {}                        # {username: writer} - подключенные пользователи


async def send_to_one(writer, message):
    """Отправка сообщения одному пользователю."""
    # в конец добавляем MSG_DELIM, чтобы клиент понял границу сообщения
    writer.write((message + MSG_DELIM).encode())

    # ждем, пока данные из буфера уйдут в сокет
    await writer.drain()                            # await - приостановка


async def send_to_everyone(message, except_username=None):
    """Отправка сообщения всем пользователям (широковещательное сообщение)."""
    dead_clients = []                           # имена пользователей, которые по какой-то причине отключились
    current_clients = list(clients.items())

    # кидаем сообщение всем подключенным пользователям
    for username, writer in current_clients:
        if username == except_username:
            continue

        try:
            writer.write((message + MSG_DELIM).encode())        # байт-строка отправляется в сокет
        except Exception:
            dead_clients.append(username)

    # ожидаем доотправки сообщений
    for username, writer in current_clients:
        if username == except_username or username in dead_clients:
            continue

        try:
            await writer.drain()
        except Exception:
            dead_clients.append(username)

    # удаляем мертвых пользователей
    for username in dead_clients:
        clients.pop(username, None)


async def send_encounter(username, encounter):
    """Отправка сообщения о встрече с монстром (одному из игроков)."""
    writer = clients.get(username)

    if writer is None:
        return

    await send_to_one(writer, make_cowsay_message(encounter))


async def move_monsters_periodically():
    """Перемещение одного случайного монстра через фиксированный промежуток времени."""
    while True:
        # первый ход происходит только после ожидания
        await asyncio.sleep(MONSTER_MOVE_INTERVAL)

        # выбираем случайного монстра и пробуем переместить его
        result = game.move_random_monster()

        # если монстров нет -> ждём следующего интервала
        if result is None:
            continue

        message = (
            f"{result['name']} moved one cell "
            f"{result['direction']}"
        )
        await send_to_everyone(message)

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

    username = None

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
        clients[username] = writer
        game.add_player(username)

        await send_to_one(writer, f"Welcome, {username}")
        await send_to_everyone(f"{username} joined the MUD", except_username=username)

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
                    message = (
                        f"{username} added monster {res['name']} "
                        f"to ({res['x']}, {res['y']}) with {res['hp']} hp"
                    )
                    if res["replaced"]:
                        message += "\nReplaced the old monster"
                    await send_to_everyone(message)

                case "no_monster":
                    if res["name"] is None:
                        await send_to_one(writer, "No monster here")
                    else:
                        await send_to_one(writer, f"No {res['name']} here")

                case "attack":
                    if res["died"]:
                        message = (
                            f"{username} attacked {res['name']} with {res['weapon']}, "
                            f"damage {res['damage']} hp, {res['name']} died"
                        )
                    else:
                        message = (
                            f"{username} attacked {res['name']} with {res['weapon']}, "
                            f"damage {res['damage']} hp, {res['name']} now has {res['hp_left']} hp"
                        )
                    await send_to_everyone(message)

                case "sayall":
                    await send_to_everyone(f"{username}: {res['message']}")

                case "error":
                    await send_to_one(writer, res["message"])

    # при любом завершении соединения удаляем игрока и рассылаем сообщение о выходе
    finally:
        was_connected = (username is not None) and (username in clients)

        if username is not None:
            clients.pop(username, None)
            game.remove_player(username)

            if was_connected:
                await send_to_everyone(f"{username} left the MUD", except_username=username)

        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def main():
    """Запуск MUD-сервер."""
    server = await asyncio.start_server(client_processing, HOST, PORT)
    asyncio.create_task(move_monsters_periodically())

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Server stopped")
