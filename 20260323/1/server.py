import cowsay, shlex, asyncio
from io import StringIO

jgsbat = cowsay.read_dot_cow(StringIO(r"""
$the_cow = <<EOC;
 ,_                    _,
 ) '-._  ,_    _,  _.-' (
 )  _.-'.|\\--//|.'-._  (
  )'   .'\/o\/o\/'.   `(
   ) .' . \====/ . '. (
    )  / <<    >> \  (
     '-._/``  ``\_.-'
jgs     __\\'--'//__
       (((""`  `"")))
EOC
"""))

MSG_DELIM = "\0"

# словарь с оружием для нанесения урона монстру
weapons = {"sword": 10, "spear": 15, "axe": 20}


# список допустимых в игре монстров
def get_monsters():
    return cowsay.list_cows() + ["jgsbat"]


class GameParam():
    def __init__(self):
        self.size = 10          # поле 10x10
        self.monsters = {}      # словарь {"name": ..., "hello": ..., "hp": ...}; ключ - (x, y)
        self.players = {}       # {username: {"x": ..., "y": ...}}  -  координаты каждого пользователя
    
    # перенос на другой край поля (если произошёл выход за границы)
    def wrap(self, coordinate):
        return coordinate % self.size
    
    # добавление нового игрока
    def add_player(self, username):
        if username in self.players:
            return False
        
        self.players[username] = {"x": 0, "y": 0}
        return True
    
    # удаление игрока
    def remove_player(self, username):
        self.players.pop(username, None)
    
    # получение координат игрока
    def get_pos(self, username):
        player = self.players[username]
        return player["x"], player["y"]
    
    # попадание игрока в клетку с монстром
    def encounter(self, x, y):
        monster = self.monsters.get((x, y))

        if monster is None:
            return
        
        # если монстр есть -> печать приветствия
        return {
                "name": monster["name"],
                "hello": monster["hello"]
        }

    # перемещения
    # перемещаем игрока по полю с учётом циклического выхода за границы
    def move(self, username, dx, dy):
        player = self.players[username]

        # серверная команда движения
        player["x"] = self.wrap(player["x"] + dx)
        player["y"] = self.wrap(player["y"] + dy)

        # отправка инфs о перемещении клиенту
        x, y = player["x"], player["y"]
        return x, y, self.encounter(x, y)

    # добавление / перезапись монстра
    def addmon(self, name, hello, hp, x, y):
        # может ли быть такой монстр в игре
        if name not in get_monsters():
            return { "status": "error", "message": "Cannot add unknown monster" }

        # перезапись монстра в клетке
        replaced = (x, y) in self.monsters
        self.monsters[(x, y)] = {"name": name, "hello": hello, "hp": hp}

        # отправка инф. о том, какой монстр теперь в этой клетке
        return {
            "status": "addmon",
            "name": name,
            "hello": hello,
            "hp": hp,
            "x": x,
            "y": y,
            "replaced": replaced
        }

    # атакуем монстра в текущей клетке игрока
    # если monster_name задан -> проверяем, что имя существует
    def attack(self, username, weapon, monster_name=None):
        if weapon not in weapons:
            return {
                "status": "error",
                "message": "Unknown weapon"
            }

        x, y = self.get_pos(username)
        monster = self.monsters.get((x, y))

        # в клеточке нет монстра
        if monster is None:
            return {
                "status": "no_monster",
                "name": monster_name
            }

        # в клеточке есть монстр, но не тот, которого написал пользователь
        if monster_name is not None and monster["name"] != monster_name:
            return {
                "status": "no_monster",
                "name": monster_name
            }

        damage = weapons[weapon]
        final_damage = min(damage, monster["hp"])
        monster["hp"] -= final_damage

        died = monster["hp"] == 0
        name = monster["name"]

        # если hp закончились -> убираем монстра из клетки
        if died:
            del self.monsters[(x, y)]

        return {
            "status": "attack",
            "name": name,
            "weapon": weapon,
            "damage": final_damage,
            "hp_left": 0 if died else monster["hp"],
            "died": died,
        }

    # разбираем одну команду клиента и возвращаем результат в виде словаря
    def process_command(self, username, line):
        if username not in self.players:
            return {
                "status": "error",
                "message": "Player is not connected"
            }

        try:
            cmd = shlex.split(line)
        except ValueError:
            return {
                "status": "error",
                "message": "Invalid arguments"
            }

        if not cmd:
            return {"status": "error", "message": "Invalid command"}

        try:
            match cmd[0]:
                case "move":
                    if len(cmd) != 3:
                        return {"status": "error", "message": "Invalid arguments"}
                    dx = int(cmd[1])
                    dy = int(cmd[2])
                    return {"status": "move", "data": self.move(username, dx, dy)}

                case "addmon":
                    if len(cmd) != 6:
                        return {"status": "error", "message": "Invalid arguments"}
                    name = cmd[1]
                    hello = cmd[2]
                    hp = int(cmd[3])
                    x = int(cmd[4])
                    y = int(cmd[5])
                    return self.addmon(name, hello, hp, x, y)

                case "attack":
                    if len(cmd) == 2:
                        weapon = cmd[1]
                        return self.attack(username, weapon)
                    if len(cmd) == 3:
                        monster_name = cmd[1]
                        weapon = cmd[2]
                        return self.attack(username, weapon, monster_name)
                    return {"status": "error", "message": "Invalid arguments"}

                case _:
                    return {"status": "error", "message": "Invalid command"}
        except ValueError:
            return {"status": "error", "message": "Invalid arguments"}


''' ----- main ----- '''

# объект, хранящий текущее состояние
game = GameParam()
clients = {}                # {username: writer} - подключенные пользователи

# сообщение одному пользователю
# в конец добавляем MSG_DELIM, чтобы клиент понял границу сообщения
async def send_to_one(writer, message):
    writer.write((message + MSG_DELIM).encode())

    # ждем, пока данные из буфера уйдут в сокет
    await writer.drain()            # await - приостановка

# сообщение всем пользователям (широковещательное сообщение)
# except_username - чтобы не отправлять сообщение самому себе
async def send_to_everyone(message, except_username=None):
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

# формируем многострочное приветствие монстра в формате cowsay
# для jgsbat используем специальный cowfile
def make_cowsay_message(encounter):
    if encounter["name"] == "jgsbat":
        return cowsay.cowsay(encounter["hello"], cowfile=jgsbat)
    return cowsay.cowsay(encounter["hello"], cow=encounter["name"])

# обработка подключения клиента
async def MUD(reader, writer):
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

# запускаем локальный сервер на 1337 порту
# клиенту нужно подключаться к 127.0.0.1:1337
async def main():
    server = await asyncio.start_server(MUD, "127.0.0.1", 1337)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Server stopped")
