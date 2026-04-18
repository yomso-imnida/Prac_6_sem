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
        return { "name": monster["name"], "hello": monster["hello"] }

    # перемещения
    def move(self, username, dx, dy):
        player = self.players[username]

        # серверная команда движения
        player["x"] = self.wrap(player["x"] + dx)
        player["y"] = self.wrap(player["y"] + dy)

        # отправка инф. о перемещении клиенту
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
        return { "status": "addmon", "name": name, "hello": hello, "hp": hp, "x": x, "y": y, "replaced": replaced }

    # атака на монстра в данной клетке
    def attack(self, username, damage, monster_name=None):
        x, y = self.get_pos(username)
        monster = self.monsters.get((x, y))

        # если монстра нет -> говорим клиенту, что его нет
        if monster is None:
            return { "status": "no_monster", "name": monster_name }
        
        # если клиент ввёл имя монстра, которого нет в этой клетке -> говорим, что такого монстра здесь нет
        if monster_name is not None and monster["name"] != monster_name:
            return { "status": "no_monster", "name": monster_name }
        
        # вычисление и нанос урона
        final_damage = min(damage, monster["hp"])
        monster["hp"] -= final_damage

        died = (monster["hp"] == 0)
        name = monster["name"]

        # смерть монстра
        if died:
            del self.monsters[(x, y)]

        # сообщаем клиенту, какой монстр с каким кол-вом hp остался в клетке
        return { "status": "attack", "name": name, "damage": final_damage,
                 "hp_left": 0 if died else monster['hp'], "died": died }
    
    # разбор командной строки, выполнение нужной команды
    def process_command(self, username, line):
        cmd = shlex.split(line)

        match cmd[0]:
            case "move":
                dx = int(cmd[1])
                dy = int(cmd[2])
                return {"status": "move", "data": self.move(username, dx, dy)}

            case "addmon":
                name = cmd[1]
                hello = cmd[2]
                hp = int(cmd[3])
                x = int(cmd[4])
                y = int(cmd[5])
                return self.addmon(name, hello, hp, x, y)

            case "attack":
                if len(cmd) == 2:
                    damage = int(cmd[1])
                    return self.attack(username, damage)
                else:
                    monster_name = cmd[1]
                    damage = int(cmd[2])
                    return self.attack(username, damage, monster_name)


''' ----- main ----- '''

# объект, хранящий текущее состояние
game = GameParam()
clients = {}                # {username: writer} - подключенные пользователи

# сообщение одному пользователю
async def send_to_one(writer, message):
    writer.write((message + "\n").encode())

    # ждем, пока данные из буфера уйдут в сокет
    await writer.drain()            # await - приостановка

# сообщение всем пользователям (широковещательное сообщение)
async def send_to_everyone(message):
    dead_clients = []                   # имена пользователей, которые по какой-то причине отключились

    # кидаем сообщение всем подключенным пользователям
    for username, writer in clients.items():
        try:
            writer.write((message + "\n").encode())             # байт-строка отправляется в сокет
        except Exception:
            dead_clients.append(username)
    
    # доотправка сообщений
    for username, writer in clients.items():
        if username not in dead_clients:                        # проверка на случай, если уже решили, что нужно удалить пользователя
            try:
                await writer.drain()
            except Exception:
                dead_clients.append(username)
    
    # удаляем мертвых пользователей
    for username in dead_clients:
        clients.pop(username, None)
        game.remove_player(username)

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
        await send_to_everyone(f"{username} joined the MUD")

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
                        if encounter["name"] == "jgsbat":
                            hello = cowsay.cowsay(encounter["hello"], cowfile=jgsbat)
                        else:
                            hello = cowsay.cowsay(encounter["hello"], cow=encounter["name"])

                        await send_to_one(writer, hello)

                case "addmon":
                    mess = (f"{username} added monster {res['name']} "
                            f"to ({res['x']}, {res['y']}) with {res['hp']} hp")
                    await send_to_everyone(mess)

                    if res["replaced"]:
                        await send_to_everyone("Replaced the old monster")

                case "no_monster":
                    if res["name"] is None:
                        await send_to_one(writer, "No monster here")
                    else:
                        await send_to_one(writer, f"No {res['name']} here")

                case "attack":
                    if res["died"]:
                        mess = (f"{username} attacked {res['name']}, damage {res['damage']} hp, "
                                f"{res['name']} died")
                    else:
                        mess = (f"{username} attacked {res['name']}, damage {res['damage']} hp, "
                                f"{res['name']} now has {res['hp_left']} hp")
                    
                    await send_to_everyone(mess)

                case "error":
                    await send_to_one(writer, res["message"])

    # при любом завершении соединения удаляем игрока и рассылаем сообщение о выходе
    finally:
        if (username is not None) and (username in clients):
            clients.pop(username, None)
            game.remove_player(username)
            await send_to_everyone(f"{username} left the MUD")

        writer.close()
        await writer.wait_closed()

# локальный сервер на 1337 порту
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
